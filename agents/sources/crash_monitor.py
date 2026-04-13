"""
CORTEX — Crash Monitor v1
Indicateurs de risque systémique et précurseurs de crash boursier

Sources gratuites (sans API key) :
  - FRED CSV : courbe des taux T10Y2Y, spread HY BAMLH0A0HYM2EY
  - Yahoo Finance : VIX, S&P500 (déjà collectés dans scout_market)
  - Calcul interne : crash_score 0–10

Score interprétation :
  0–3  → 🟢 Risque faible
  4–6  → 🟡 Vigilance
  7–10 → 🔴 Risque élevé
"""

import asyncio
import httpx
import csv
import io
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger("crash_monitor")

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = {
    "yield_curve":  "T10Y2Y",          # Spread 10Y-2Y (inversion = récession signal)
    "hy_spread":    "BAMLH0A0HYM2EY",  # High-yield bond spread (stress crédit)
}


# ── Fetchers FRED ──────────────────────────────────────────────────────────────

async def _fetch_fred_series(client: httpx.AsyncClient, series_id: str) -> float | None:
    """Récupère la dernière valeur d'une série FRED via CSV."""
    try:
        r = await client.get(
            FRED_BASE,
            params={"id": series_id},
            timeout=15,
        )
        if r.status_code != 200:
            return None

        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        # CSV format: DATE,VALUE — skip header, take last non-empty row
        for row in reversed(rows[1:]):
            if len(row) == 2 and row[1].strip() not in (".", ""):
                try:
                    return float(row[1])
                except ValueError:
                    continue
        return None
    except Exception as e:
        logger.warning(f"FRED {series_id}: {e}")
        return None


# ── Score calculation ──────────────────────────────────────────────────────────

def _compute_crash_score(yield_curve: float | None, hy_spread: float | None, vix: float | None) -> dict:
    """
    Calcule un score de risque crash 0–10 à partir des indicateurs disponibles.

    Pondération :
      - Courbe des taux (T10Y2Y) : 40 pts max
      - Spread HY                 : 35 pts max
      - VIX                       : 25 pts max
    """
    score = 0.0
    factors = []

    # Courbe des taux (T10Y2Y)
    # < -0.5 → inversion prononcée → score max
    # -0.5 à 0 → zone de vigilance
    # > 0 → normale
    if yield_curve is not None:
        if yield_curve < -1.0:
            pts = 4.0
            label = f"Courbe inversée ({yield_curve:+.2f}%) — signal récession fort"
        elif yield_curve < -0.5:
            pts = 3.0
            label = f"Courbe inversée ({yield_curve:+.2f}%) — vigilance"
        elif yield_curve < 0:
            pts = 1.5
            label = f"Courbe légèrement inversée ({yield_curve:+.2f}%)"
        else:
            pts = 0.0
            label = f"Courbe normale ({yield_curve:+.2f}%)"
        score += pts
        factors.append({"indicator": "Courbe 10Y-2Y", "value": f"{yield_curve:+.2f}%", "points": pts, "label": label})

    # Spread HY (BAMLH0A0HYM2EY) — en points de base (%)
    # > 6% → stress crédit élevé
    # 4–6% → zone de vigilance
    # < 4% → normal
    if hy_spread is not None:
        if hy_spread > 8.0:
            pts = 3.5
            label = f"Spread HY {hy_spread:.1f}% — stress crédit extrême"
        elif hy_spread > 6.0:
            pts = 2.5
            label = f"Spread HY {hy_spread:.1f}% — stress crédit élevé"
        elif hy_spread > 4.5:
            pts = 1.5
            label = f"Spread HY {hy_spread:.1f}% — vigilance"
        else:
            pts = 0.0
            label = f"Spread HY {hy_spread:.1f}% — normal"
        score += pts
        factors.append({"indicator": "Spread HY", "value": f"{hy_spread:.1f}%", "points": pts, "label": label})

    # VIX
    # > 35 → panique → score max
    # 25–35 → stress élevé
    # 20–25 → nervosité
    # < 20 → normal
    if vix is not None:
        if vix > 40:
            pts = 2.5
            label = f"VIX {vix:.0f} — panique marché"
        elif vix > 30:
            pts = 2.0
            label = f"VIX {vix:.0f} — stress élevé"
        elif vix > 25:
            pts = 1.2
            label = f"VIX {vix:.0f} — nervosité"
        elif vix > 20:
            pts = 0.5
            label = f"VIX {vix:.0f} — légère tension"
        else:
            pts = 0.0
            label = f"VIX {vix:.0f} — calme"
        score += pts
        factors.append({"indicator": "VIX", "value": f"{vix:.1f}", "points": pts, "label": label})

    final_score = round(min(score, 10.0), 1)

    if final_score <= 3:
        color = "🟢"
        interpretation = "Risque systémique faible"
    elif final_score <= 6:
        color = "🟡"
        interpretation = "Zone de vigilance"
    else:
        color = "🔴"
        interpretation = "Risque crash élevé"

    return {
        "crash_score":    final_score,
        "color":          color,
        "interpretation": interpretation,
        "factors":        factors,
        "yield_curve":    yield_curve,
        "hy_spread":      hy_spread,
        "vix":            vix,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }


# ── Point d'entrée ─────────────────────────────────────────────────────────────

async def collect(vix: float | None = None) -> dict:
    """
    Lance la collecte des indicateurs crash.

    Args:
        vix: valeur VIX déjà collectée par scout_market (évite une double requête)

    Returns:
        dict avec crash_score, color, interpretation, factors
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(headers=headers) as client:
        yield_curve, hy_spread = await asyncio.gather(
            _fetch_fred_series(client, FRED_SERIES["yield_curve"]),
            _fetch_fred_series(client, FRED_SERIES["hy_spread"]),
            return_exceptions=True,
        )

    if isinstance(yield_curve, Exception):
        yield_curve = None
    if isinstance(hy_spread, Exception):
        hy_spread = None

    result = _compute_crash_score(yield_curve, hy_spread, vix)

    logger.info(
        f"Crash Monitor: score={result['crash_score']}/10 {result['color']} | "
        f"yield_curve={yield_curve} | hy_spread={hy_spread} | vix={vix}"
    )
    return result
