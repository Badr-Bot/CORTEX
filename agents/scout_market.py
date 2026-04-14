"""
CORTEX — Agent SCOUT-MARKET v2
Collecte : dashboard marchés temps réel + signaux news macro

Sources :
  - yfinance (Yahoo Finance via librairie Python) — S&P500, Nasdaq, Or, Pétrole, DXY, VIX, US 10Y
  - RSS : Reuters Markets, FT Markets, MarketWatch, Seeking Alpha, Yahoo Finance
"""

import asyncio
import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.market")

TICKERS = {
    "sp500":   "^GSPC",
    "nasdaq":  "^IXIC",
    "gold":    "GC=F",
    "oil":     "CL=F",
    "dxy":     "DX-Y.NYB",
    "vix":     "^VIX",
    "us_10y":  "^TNX",
}

MARKET_NEWS_FEEDS = [
    {"name": "Reuters Markets",  "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "MarketWatch",      "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "Yahoo Finance",    "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Seeking Alpha",    "url": "https://seekingalpha.com/market_currents.xml"},
    {"name": "FT Markets",       "url": "https://www.ft.com/rss/home/uk"},
]

MARKET_KEYWORDS = [
    "fed", "federal reserve", "rate", "inflation", "gdp", "recession",
    "earnings", "s&p", "nasdaq", "dow", "equity", "bond", "yield",
    "dollar", "dxy", "gold", "oil", "crude", "vix", "volatility",
    "macro", "jobs", "nfp", "cpi", "pce", "fomc", "pivot", "taper",
    "market", "stock", "rally", "selloff", "correction", "bear", "bull",
    "china", "europe", "ecb", "tariff", "trade war", "geopolitical",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_market_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in MARKET_KEYWORDS)


def _vix_interpretation(vix: float) -> str:
    if vix < 15:   return "Complaisance extrême"
    if vix < 20:   return "Calme"
    if vix < 25:   return "Légère nervosité"
    if vix < 30:   return "Volatilité élevée"
    if vix < 40:   return "Stress marché"
    return "Panique"


def _direction_arrow(change_pct: float) -> str:
    return "▴" if change_pct >= 0 else "▾"


def _format_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


# ── Collecte dashboard (yfinance — robuste aux changements Yahoo) ─────────────

def _price_str(key: str, price: float) -> str:
    """Formate le prix selon le ticker."""
    if key == "gold":
        return f"${price:,.0f}"
    if key == "oil":
        return f"${price:.1f}"
    if key in ("dxy",):
        return f"{price:.2f}"
    if key == "vix":
        return f"{price:.2f}"
    if key == "us_10y":
        return f"{price:.3f}%"
    return f"{price:,.2f}"


def _fetch_ticker_sync(key: str, symbol: str) -> tuple[str, dict]:
    """
    Récupère prix + variation 1j via yfinance.
    yfinance gère automatiquement les cookies Yahoo Finance.
    Exécuté dans un thread séparé (bloquant).
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period="5d", interval="1d", auto_adjust=True)

        if hist.empty:
            raise ValueError(f"Aucune donnée pour {symbol}")

        price = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0

        return key, {
            "price":      _price_str(key, price),
            "change_pct": round(change_pct, 2),
            "raw_price":  price,
        }
    except Exception as e:
        logger.warning(f"yfinance [{key}/{symbol}]: {e}")
        return key, {"price": "N/A", "change_pct": 0.0, "raw_price": 0.0}


async def _fetch_ticker(key: str, symbol: str) -> tuple[str, dict]:
    """Wrapper async pour _fetch_ticker_sync."""
    return await asyncio.to_thread(_fetch_ticker_sync, key, symbol)


async def collect_dashboard() -> dict:
    """
    Récupère tous les indicateurs marché en parallèle via yfinance.
    yfinance est plus robuste que l'API brute Yahoo Finance car il gère
    automatiquement les cookies, crumbs et changements d'API.
    """
    tasks = [_fetch_ticker(k, v) for k, v in TICKERS.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    dashboard = {}
    for r in results:
        if isinstance(r, tuple):
            key, data = r
            dashboard[key] = data
        elif isinstance(r, Exception):
            logger.warning(f"Erreur inattendue collecte ticker: {r}")

    # Calculer variation 10Y en bps (points de base)
    if "us_10y" in dashboard:
        chg = dashboard["us_10y"].get("change_pct", 0)
        raw = dashboard["us_10y"].get("raw_price", 4.5)
        # Approximation : si variation est en %, convertir en bps du taux
        bps = round(chg * raw / 100 * 100, 1)
        sign = "+" if bps >= 0 else ""
        dashboard["us_10y"]["change_bps"] = f"{sign}{bps:.0f}bps"

    # VIX interprétation
    if "vix" in dashboard:
        vix_val = dashboard["vix"].get("raw_price", 20.0)
        dashboard["vix"]["interpretation"] = _vix_interpretation(float(vix_val))

    sp_price = dashboard.get("sp500", {}).get("price", "N/A")
    sp_chg   = dashboard.get("sp500", {}).get("change_pct", 0)
    vix_p    = dashboard.get("vix",   {}).get("price", "N/A")
    logger.info(
        f"Dashboard marché: S&P {sp_price} ({_format_pct(sp_chg)}), VIX {vix_p}"
    )
    return dashboard


# ── Collecte signaux news ─────────────────────────────────────────────────────

async def _fetch_rss_feed(feed_info: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = []
    try:
        feed = await asyncio.to_thread(feedparser.parse, feed_info["url"])
        for entry in feed.entries[:15]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                try:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            title   = entry.get("title", "").strip()
            url     = entry.get("link", "")
            content = entry.get("summary", entry.get("description", ""))[:400]

            if not title or not url:
                continue
            if not _is_market_relevant(title + " " + content):
                continue

            signals.append({
                "title":       title,
                "source_name": feed_info["name"],
                "source_url":  url,
                "raw_content": content,
                "sector":      "market",
                "category":    "media",
            })
    except Exception as e:
        logger.warning(f"Market RSS {feed_info['name']}: {e}")
    return signals


async def collect_signals(hours: int = 24) -> list[dict]:
    """Collecte les signaux news marchés depuis tous les flux RSS."""
    results = await asyncio.gather(
        *[_fetch_rss_feed(f, hours) for f in MARKET_NEWS_FEEDS],
        return_exceptions=True,
    )
    signals = []
    for r in results:
        if isinstance(r, list):
            signals.extend(r)

    # Déduplication
    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    logger.info(f"SCOUT-MARKET signaux: {len(unique)} news ({hours}h)")
    return unique


# ── Point d'entrée principal ──────────────────────────────────────────────────

async def collect(hours: int = 24) -> dict:  # noqa: E302
    """
    Lance la collecte complète SCOUT-MARKET.
    Retourne : {dashboard: dict, signals: list[dict], hot_stocks: list[dict], crash: dict}
    """
    from agents.sources.stock_screener import collect as collect_stocks
    from agents.sources.crash_monitor import collect as collect_crash

    dashboard, signals, hot_stocks = await asyncio.gather(
        collect_dashboard(),
        collect_signals(hours),
        collect_stocks(hours),
    )

    # Passe le VIX déjà collecté pour éviter une double requête
    vix_raw = dashboard.get("vix", {}).get("raw_price") if isinstance(dashboard, dict) else None
    crash = await collect_crash(vix=vix_raw)

    logger.info(
        f"SCOUT-MARKET: {len(hot_stocks)} actions chaudes | "
        f"crash score={crash.get('crash_score', '?')}/10 {crash.get('color', '')}"
    )
    return {"dashboard": dashboard, "signals": signals, "hot_stocks": hot_stocks, "crash": crash}
