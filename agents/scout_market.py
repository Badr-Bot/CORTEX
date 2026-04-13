"""
CORTEX — Agent SCOUT-MARKET v1
Collecte : dashboard marchés temps réel + signaux news macro

Sources :
  - Yahoo Finance API (gratuit, sans clé) — S&P500, Nasdaq, Or, Pétrole, DXY, VIX, US 10Y
  - RSS : Reuters Markets, FT Markets, MarketWatch, Seeking Alpha, Yahoo Finance
"""

import asyncio
import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.market")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

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


# ── Collecte dashboard (Yahoo Finance) ───────────────────────────────────────

async def _fetch_ticker(client: httpx.AsyncClient, key: str, symbol: str) -> tuple[str, dict]:
    """Récupère prix actuel + variation 1j pour un ticker Yahoo Finance."""
    try:
        r = await client.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={"interval": "1d", "range": "5d"},
            timeout=10,
        )
        data = r.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})

        price = meta.get("regularMarketPrice", 0)
        prev  = meta.get("previousClose", price) or price
        change_pct = ((price - prev) / prev * 100) if prev else 0

        # Formatting selon le ticker
        if key == "gold":
            price_str = f"${price:,.0f}"
        elif key == "oil":
            price_str = f"${price:.1f}"
        elif key in ("dxy",):
            price_str = f"{price:.1f}"
        elif key == "vix":
            price_str = f"{price:.1f}"
        elif key == "us_10y":
            price_str = f"{price:.2f}%"
        else:
            price_str = f"{price:,.0f}"

        return key, {
            "price":      price_str,
            "change_pct": change_pct,
            "raw_price":  price,
        }
    except Exception as e:
        logger.warning(f"Yahoo Finance {symbol}: {e}")
        return key, {"price": "N/A", "change_pct": 0.0, "raw_price": 0}


async def collect_dashboard() -> dict:
    """Récupère tous les indicateurs marché en parallèle via Yahoo Finance."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [_fetch_ticker(client, k, v) for k, v in TICKERS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    dashboard = {}
    for r in results:
        if isinstance(r, tuple):
            key, data = r
            dashboard[key] = data

    # Calculer variation 10Y en bps
    if "us_10y" in dashboard:
        chg = dashboard["us_10y"].get("change_pct", 0)
        raw = dashboard["us_10y"].get("raw_price", 4.0)
        bps = round(raw * chg / 100 * 100, 1)  # approximate bps
        dashboard["us_10y"]["change_bps"] = f"{'+' if bps >= 0 else ''}{bps:.0f}bps"

    # VIX interprétation
    if "vix" in dashboard:
        vix_val = dashboard["vix"].get("raw_price", 20)
        dashboard["vix"]["interpretation"] = _vix_interpretation(vix_val)

    logger.info(
        f"Dashboard marché: S&P {dashboard.get('sp500', {}).get('price', 'N/A')}, "
        f"VIX {dashboard.get('vix', {}).get('price', 'N/A')}"
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

async def collect(hours: int = 24) -> dict:
    """
    Lance la collecte complète SCOUT-MARKET.
    Retourne : {dashboard: dict, signals: list[dict]}
    """
    dashboard, signals = await asyncio.gather(
        collect_dashboard(),
        collect_signals(hours),
    )
    return {"dashboard": dashboard, "signals": signals}
