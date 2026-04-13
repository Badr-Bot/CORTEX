"""
CORTEX — Stock Screener
Détecte les actions avec fort momentum (hausse ou chute brutale).
Utilise yfinance (gratuit, sans clé API).

Retourne : liste de dicts {ticker, name, price, change_1d, change_5d, reason}
"""

import asyncio
from utils.logger import get_logger

logger = get_logger("scout_ai.stock_screener")

# Univers de stocks à surveiller (croissance + momentum + IA + crypto-adjacent)
WATCHLIST = [
    # IA & Semi-conducteurs
    "NVDA", "AMD", "ARM", "AVGO", "MRVL", "SMCI",
    # Big Tech
    "META", "GOOGL", "MSFT", "AMZN", "AAPL", "TSLA",
    # SaaS croissance
    "NOW", "CRM", "SNOW", "PLTR", "CRWD", "NET", "DDOG", "MDB",
    # Crypto-adjacent
    "COIN", "MSTR", "HOOD",
    # Biotech / DeepTech
    "MRNA", "NVAX",
    # ETF volatils
    "SOXL", "TQQQ",
]

# Labels sectoriels pour l'explication
SECTOR_LABELS = {
    "NVDA": "Semi-conducteurs IA", "AMD": "Semi-conducteurs", "ARM": "Architecture puces IA",
    "AVGO": "Semi-conducteurs", "MRVL": "Semi-conducteurs", "SMCI": "Serveurs IA",
    "META": "Big Tech / IA", "GOOGL": "Big Tech / IA", "MSFT": "Big Tech / IA",
    "AMZN": "Cloud / E-commerce", "AAPL": "Big Tech", "TSLA": "EV / IA",
    "NOW": "SaaS Entreprise", "CRM": "SaaS CRM", "SNOW": "Data Cloud",
    "PLTR": "Data / Défense IA", "CRWD": "Cybersécurité", "NET": "Réseau cloud",
    "DDOG": "Observabilité", "MDB": "Base de données",
    "COIN": "Exchange crypto", "MSTR": "Bitcoin trésorerie", "HOOD": "Brokerage",
    "MRNA": "Biotech ARNm", "NVAX": "Biotech vaccins",
    "SOXL": "ETF Semi-conducteurs x3", "TQQQ": "ETF Nasdaq x3",
}


async def collect(hours: int = 24) -> list[dict]:
    """
    Screene les actions avec le plus fort mouvement sur 1j et 5j.
    Retourne les top 5 mouvements (haussiers ou baissiers).
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(None, _screen_sync)
    except Exception as e:
        logger.error(f"Stock screener erreur: {e}")
        return []


def _screen_sync() -> list[dict]:
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance non installé — stock screener désactivé")
        return []

    results = []

    try:
        # Téléchargement en batch (rapide)
        tickers_str = " ".join(WATCHLIST)
        data = yf.download(
            tickers_str,
            period="7d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True,
        )

        if data.empty:
            return []

        close = data.get("Close", data)

        for ticker in WATCHLIST:
            try:
                if ticker not in close.columns:
                    continue

                prices = close[ticker].dropna()
                if len(prices) < 2:
                    continue

                current = float(prices.iloc[-1])
                prev    = float(prices.iloc[-2])
                start5d = float(prices.iloc[0])

                change_1d = (current - prev) / prev * 100
                change_5d = (current - start5d) / start5d * 100

                # Ne garder que les mouvements significatifs
                if abs(change_1d) < 2.0 and abs(change_5d) < 4.0:
                    continue

                results.append({
                    "ticker":    ticker,
                    "name":      SECTOR_LABELS.get(ticker, ticker),
                    "price":     round(current, 2),
                    "change_1d": round(change_1d, 1),
                    "change_5d": round(change_5d, 1),
                    "reason":    "",  # Rempli par Claude dans l'analyse marché
                })

            except Exception:
                continue

    except Exception as e:
        logger.warning(f"yfinance download échoué: {e}")
        return []

    # Trier par amplitude de mouvement 1 jour
    results.sort(key=lambda x: abs(x["change_1d"]), reverse=True)
    top = results[:5]

    if top:
        logger.info(f"Stock screener: {len(results)} mouvements détectés, top 5 retenus")
    else:
        logger.info("Stock screener: aucun mouvement significatif aujourd'hui")

    return top
