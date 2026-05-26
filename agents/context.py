"""
CORTEX — Mémoire contextuelle légère (14 jours glissants)

Stocke les 2-3 signaux clés par secteur chaque jour dans data/context.json.
Injecté dans les prompts Claude pour que l'analyse soit ancrée dans le passé récent.

Format :
{
  "2026-05-25": {
    "ai":       ["GPT-5 lancé en preview — impact GPU stocks +8%", ...],
    "crypto":   ["BTC teste support $95k après liquidations $2.3B", ...],
    "market":   ["Fed minutes hawkish — taux 10Y remontent à 4.5%", ...],
    "deeptech": ["DeepMind annonce AlphaFold 3 — 300M protéines mappées", ...]
  },
  ...
}
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

CONTEXT_FILE = Path(__file__).parent.parent / "data" / "context.json"
WINDOW_DAYS  = 14


def _load() -> dict:
    if CONTEXT_FILE.exists():
        try:
            return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _purge_old(data: dict) -> dict:
    cutoff = (datetime.now() - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    return {date: v for date, v in data.items() if date >= cutoff}


def _extract_bullets(sector_data: dict, max_signals: int = 3) -> list[str]:
    bullets = []
    for sig in sector_data.get("signals", [])[:max_signals]:
        title = sig.get("title", "").strip()
        fait  = sig.get("fait",  "").strip()
        if title:
            short = fait[:120] if fait else ""
            bullets.append(f"{title} — {short}" if short else title)
    return bullets


def save_daily(ai: dict, crypto: dict, market: dict, deeptech: dict) -> None:
    """Sauvegarde le contexte du jour (appelé après le rapport du matin)."""
    data = _purge_old(_load())
    today = datetime.now().strftime("%Y-%m-%d")
    data[today] = {
        "ai":       _extract_bullets(ai),
        "crypto":   _extract_bullets(crypto),
        "market":   _extract_bullets(market),
        "deeptech": _extract_bullets(deeptech),
    }
    _save(data)


def load_context(sector: str, days: int = 14) -> str:
    """
    Retourne un bloc texte compact des événements récents pour un secteur.
    Ex :
      CONTEXTE 7 DERNIERS JOURS :
      [2026-05-25] GPT-5 lancé — impact GPU stocks +8%
      [2026-05-24] OpenAI lève $5B — valorisation $200B
    """
    data = _purge_old(_load())
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    lines = []
    for date in sorted(data.keys(), reverse=True):
        if date < cutoff:
            break
        bullets = data[date].get(sector, [])
        for b in bullets:
            lines.append(f"[{date}] {b}")

    if not lines:
        return ""

    header = f"CONTEXTE {min(days, 14)} DERNIERS JOURS (ne pas répéter, utiliser comme fond) :"
    return header + "\n" + "\n".join(lines[:20])
