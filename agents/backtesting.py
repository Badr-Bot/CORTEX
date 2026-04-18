"""
CORTEX — Backtesting des signaux

Concept : Chaque jour CORTEX génère des signaux avec recommandations (ACHETER, SURVEILLER…).
Le dimanche on vérifie si les prix ont bougé dans la bonne direction depuis le signal.

Table Supabase requise :
    signal_predictions(
        id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        report_date  text,
        sector       text,
        ticker       text,
        signal_title text,
        direction    text,    -- BUY | SELL | NEUTRAL
        price_at_signal float,
        price_current   float,
        result       text,    -- correct | incorrect | partial | pending
        created_at   timestamptz DEFAULT now()
    )

Si la table n'existe pas : log WARNING et continue sans crasher.
"""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("backtesting")

# ── Patterns pour extraire les tickers depuis le champ "action" ───────────────
# Mots en MAJUSCULES de 2 à 5 caractères, précédés d'un espace ou début de string
_TICKER_RE = re.compile(r"(?<![A-Z])([A-Z]{2,5})(?![A-Z])")

# Tickers à ignorer (mots courants en majuscules dans les textes français/anglais)
_TICKER_BLOCKLIST = {
    "BUY", "SELL", "USD", "EUR", "GBP", "JPY", "ETF", "IPO", "CEO", "CFO",
    "HOLD", "USA", "EU", "UK", "IA", "AI", "LLM", "API", "GPU", "CPU",
    "EPS", "PE", "ATH", "ATL", "YTD", "QoQ", "YoY", "NFP", "CPI", "PCE",
    "FED", "ECB", "IMF", "SEC", "ETH", "DXY", "VIX", "SPY", "QQQ",
    "FOMC", "OPEC", "NATO", "WHO", "FDA", "AWS", "GCP", "MSFT", "AAPL",
    "GOOG", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "QCOM",
}

# Correspondances BTC/ETH → tickers Yahoo Finance
_CRYPTO_MAP = {
    "BTC":  "BTC-USD",
    "ETH":  "ETH-USD",
    "SOL":  "SOL-USD",
    "BNB":  "BNB-USD",
    "XRP":  "XRP-USD",
    "DOGE": "DOGE-USD",
    "ADA":  "ADA-USD",
    "AVAX": "AVAX-USD",
}


# ── Extraction des tickers ────────────────────────────────────────────────────

def _extract_ticker(action: str) -> str | None:
    """
    Parse le champ 'action' d'un signal pour trouver un ticker.
    Ex: "ACHETER NVDA sous 900$" → "NVDA"
         "Surveiller BTC au-dessus de 70k" → "BTC-USD"
    Retourne None si aucun ticker trouvé.
    """
    if not action:
        return None
    candidates = _TICKER_RE.findall(action)
    for c in candidates:
        if c in _TICKER_BLOCKLIST:
            continue
        # Crypto mapping
        if c in _CRYPTO_MAP:
            return _CRYPTO_MAP[c]
        return c
    return None


def _extract_direction(action: str) -> str:
    """
    Déduit la direction (BUY / SELL / NEUTRAL) depuis le texte de l'action.
    """
    if not action:
        return "NEUTRAL"
    text = action.lower()
    buy_kw  = ["acheter", "buy", "long", "accumul", "hausse", "bullish", "breakout haussier"]
    sell_kw = ["vendre", "sell", "short", "baisse", "bearish", "éviter", "sortir", "couper"]
    for kw in sell_kw:
        if kw in text:
            return "SELL"
    for kw in buy_kw:
        if kw in text:
            return "BUY"
    return "NEUTRAL"


# ── Prix via Yahoo Finance ────────────────────────────────────────────────────

async def _fetch_price_yf(ticker: str, date: str | None = None) -> float | None:
    """
    Récupère le prix d'un ticker via Yahoo Finance (chart API, sans clé).
    - Si date fournie (YYYY-MM-DD) → prix de clôture ce jour-là (historique).
    - Si date None → prix actuel.
    Retourne None en cas d'erreur.
    """
    try:
        import httpx
        YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        if date:
            # Historique : range autour de la date
            dt = datetime.strptime(date, "%Y-%m-%d")
            period1 = int((dt - timedelta(days=1)).timestamp())
            period2 = int((dt + timedelta(days=2)).timestamp())
            params = {"interval": "1d", "period1": period1, "period2": period2}
        else:
            params = {"interval": "1d", "range": "1d"}

        async with httpx.AsyncClient(headers=headers) as client:
            r = await client.get(
                YAHOO_CHART.format(symbol=ticker),
                params=params,
                timeout=10,
            )
        data = r.json()
        result = data.get("chart", {}).get("result", [{}])[0]

        if date:
            quotes = result.get("indicators", {}).get("quote", [{}])
            closes = [c for c in (quotes[0].get("close") or []) if c is not None] if quotes else []
            return round(closes[-1], 4) if closes else None
        else:
            price = result.get("meta", {}).get("regularMarketPrice")
            return round(price, 4) if price else None

    except Exception as e:
        logger.debug(f"YF price {ticker} @{date}: {e}")
        return None


# ── Supabase gracieux ─────────────────────────────────────────────────────────

def _is_table_missing(exc: Exception) -> bool:
    """Détecte si l'exception est due à une table absente (PGRST205 / schema cache)."""
    msg = str(exc)
    return "PGRST205" in msg or "schema cache" in msg or "does not exist" in msg or "relation" in msg


def _get_supabase():
    """Retourne le client Supabase ou None si configuration manquante."""
    try:
        from database.client import get_supabase_client
        return get_supabase_client()
    except Exception as e:
        logger.warning(f"Supabase client unavailable: {e}")
        return None


# ── API publique ──────────────────────────────────────────────────────────────

async def save_signal_predictions(report_json: dict, report_date: str) -> None:
    """
    Sauvegarde les prédictions des signaux dans Supabase table 'signal_predictions'.
    Appelée après génération du rapport quotidien.

    Pour chaque signal ayant un ticker identifiable dans le champ 'action',
    enregistre : ticker, direction attendue, prix au moment du signal.

    Args:
        report_json : dict du rapport (clés : ai, crypto, market, deeptech, nexus)
        report_date : date YYYY-MM-DD du rapport
    """
    db = _get_supabase()
    if not db:
        return

    records_to_insert = []

    # Parcourir tous les secteurs du rapport
    for sector, sector_data in report_json.items():
        if not isinstance(sector_data, dict):
            continue
        signals = sector_data.get("signals", [])
        if not signals:
            continue

        for signal in signals:
            action = signal.get("action", "") or signal.get("recommendation", "")
            title  = signal.get("title", "")[:200]

            ticker = _extract_ticker(action)
            if not ticker:
                continue

            direction = _extract_direction(action)

            # Récupérer le prix au moment du signal
            price_at_signal = await _fetch_price_yf(ticker, date=report_date)

            records_to_insert.append({
                "report_date":    report_date,
                "sector":         sector,
                "ticker":         ticker,
                "signal_title":   title,
                "direction":      direction,
                "price_at_signal": price_at_signal,
                "price_current":   None,
                "result":         "pending",
            })

    if not records_to_insert:
        logger.info(f"Backtesting: aucun ticker identifiable dans le rapport du {report_date}")
        return

    try:
        db.table("signal_predictions").insert(records_to_insert).execute()
        logger.info(
            f"Backtesting: {len(records_to_insert)} prédictions sauvegardées pour {report_date}"
        )
    except Exception as e:
        if _is_table_missing(e):
            logger.warning("WARNING: table signal_predictions not found, backtesting skipped")
        else:
            logger.error(f"Erreur save_signal_predictions: {e}")


async def evaluate_predictions(days_back: int = 7) -> dict:
    """
    Récupère les prédictions de la semaine depuis Supabase.
    Pour chaque prédiction, fetch le prix actuel vs prix au signal.
    Calcule : correct / incorrect / partial / pending.
    Retourne un résumé avec taux de réussite.

    Args:
        days_back : fenêtre en jours (défaut 7)

    Returns:
        dict {total, correct, incorrect, partial, pending, taux_reussite, details}
    """
    db = _get_supabase()
    if not db:
        return {}

    # Récupérer les prédictions de la semaine
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        result = (
            db.table("signal_predictions")
            .select("*")
            .gte("report_date", cutoff)
            .execute()
        )
        predictions = result.data or []
    except Exception as e:
        if _is_table_missing(e):
            logger.warning("WARNING: table signal_predictions not found, backtesting skipped")
        else:
            logger.error(f"Erreur récupération prédictions: {e}")
        return {}

    if not predictions:
        logger.info("Backtesting: aucune prédiction trouvée pour la semaine")
        return {}

    # Évaluer chaque prédiction
    counts = {"correct": 0, "incorrect": 0, "partial": 0, "pending": 0}
    details = []

    for pred in predictions:
        ticker         = pred.get("ticker", "")
        direction      = pred.get("direction", "NEUTRAL")
        price_at_sig   = pred.get("price_at_signal")
        pred_id        = pred.get("id")

        # Fetch prix actuel
        price_now = await _fetch_price_yf(ticker)

        verdict = "pending"
        change_pct = None

        if price_at_sig and price_now and price_at_sig > 0:
            change_pct = (price_now - price_at_sig) / price_at_sig * 100

            if direction == "BUY":
                if change_pct >= 2:
                    verdict = "correct"
                elif change_pct <= -2:
                    verdict = "incorrect"
                elif 0 < change_pct < 2:
                    verdict = "partial"
                else:
                    verdict = "incorrect"
            elif direction == "SELL":
                if change_pct <= -2:
                    verdict = "correct"
                elif change_pct >= 2:
                    verdict = "incorrect"
                elif -2 < change_pct < 0:
                    verdict = "partial"
                else:
                    verdict = "incorrect"
            else:
                # NEUTRAL — mouvement fort = incorrect, stable = correct
                verdict = "correct" if abs(change_pct) < 3 else "partial"

        counts[verdict] = counts.get(verdict, 0) + 1

        details.append({
            "ticker":         ticker,
            "direction":      direction,
            "price_at_signal": price_at_sig,
            "price_current":  price_now,
            "change_pct":     round(change_pct, 2) if change_pct is not None else None,
            "result":         verdict,
            "signal_title":   pred.get("signal_title", ""),
            "sector":         pred.get("sector", ""),
        })

        # Mettre à jour dans Supabase si on a un résultat définitif
        if pred_id and verdict != "pending":
            try:
                db.table("signal_predictions").update({
                    "price_current": price_now,
                    "result":        verdict,
                }).eq("id", pred_id).execute()
            except Exception as e:
                logger.debug(f"Update prédiction {pred_id}: {e}")

    total = len(predictions)
    evaluated = total - counts["pending"]
    taux = 0
    if evaluated > 0:
        taux = round(
            (counts["correct"] + counts["partial"] * 0.5) / evaluated * 100
        )

    summary = {
        "total":        total,
        "correct":      counts["correct"],
        "incorrect":    counts["incorrect"],
        "partial":      counts["partial"],
        "pending":      counts["pending"],
        "taux_reussite": taux,
        "details":      details,
    }

    logger.info(
        f"Backtesting évalué: {total} signaux, "
        f"{counts['correct']} corrects, {counts['incorrect']} incorrects, "
        f"{counts['partial']} partiels — taux {taux}%"
    )
    return summary


async def get_backtesting_summary() -> str:
    """
    Retourne un résumé texte du backtesting à injecter dans le weekly bilan.
    Ex: "Cette semaine : 5 signaux, 3 corrects (60%), 1 partiel, 1 incorrect"

    Retourne une chaîne vide si aucune donnée disponible.
    """
    try:
        summary = await evaluate_predictions(days_back=7)
        if not summary or summary.get("total", 0) == 0:
            return ""

        total    = summary["total"]
        correct  = summary["correct"]
        partial  = summary["partial"]
        incorrect = summary["incorrect"]
        pending  = summary["pending"]
        taux     = summary["taux_reussite"]

        parts = [f"Cette semaine : {total} signal(s) backtesté(s)"]
        parts.append(f"{correct} correct(s) ({taux}% de réussite)")
        if partial:
            parts.append(f"{partial} partiel(s)")
        if incorrect:
            parts.append(f"{incorrect} incorrect(s)")
        if pending:
            parts.append(f"{pending} en attente de prix")

        return ", ".join(parts)

    except Exception as e:
        logger.warning(f"get_backtesting_summary échoué (non bloquant): {e}")
        return ""
