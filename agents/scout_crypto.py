"""
CORTEX — Agent SCOUT-CRYPTO v1
Collecte : dashboard temps réel + signaux news crypto

Sources :
  - CoinGecko API (global, prix BTC) — gratuit, sans clé
  - Alternative.me (Fear & Greed) — gratuit
  - Binance Futures API (funding rates) — gratuit
  - RSS : CoinDesk, The Block, Decrypt, CryptoPanic
"""

import asyncio
import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.crypto")

COINGECKO_BASE  = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL  = "https://api.alternative.me/fng/?limit=1"
BINANCE_FUND_URL = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"

CRYPTO_NEWS_FEEDS = [
    {"name": "CoinDesk",    "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "The Block",   "url": "https://www.theblock.co/rss.xml"},
    {"name": "Decrypt",     "url": "https://decrypt.co/feed"},
    {"name": "CryptoPanic", "url": "https://cryptopanic.com/news/rss/"},
]

CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "defi", "nft",
    "blockchain", "solana", "stablecoin", "sec", "etf", "halving",
    "whale", "exchange", "binance", "coinbase", "layer2", "web3",
    "altcoin", "on-chain", "wallet", "hack", "regulation", "cbdc",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_crypto_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in CRYPTO_KEYWORDS)


def _fear_greed_label(score: int) -> str:
    if score < 20:  return "Peur extrême"
    if score < 40:  return "Peur"
    if score < 60:  return "Neutre"
    if score < 80:  return "Avidité"
    return "Avidité extrême"


# ── Collecte dashboard (données temps réel) ───────────────────────────────────

async def _fetch_coingecko_global(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(f"{COINGECKO_BASE}/global", timeout=10)
        data = r.json().get("data", {})
        return {
            "btc_dominance":      round(data.get("market_cap_percentage", {}).get("btc", 0), 1),
            "total_volume_24h":   data.get("total_volume", {}).get("usd", 0),
            "market_cap_change":  round(data.get("market_cap_change_percentage_24h_usd", 0), 1),
        }
    except Exception as e:
        logger.warning(f"CoinGecko global: {e}")
        return {}


async def _fetch_btc_price(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10,
        )
        btc = r.json().get("bitcoin", {})
        return {
            "btc_price":     btc.get("usd", 0),
            "btc_change_24h": round(btc.get("usd_24h_change", 0), 1),
        }
    except Exception as e:
        logger.warning(f"BTC price: {e}")
        return {}


async def _fetch_fear_greed(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(FEAR_GREED_URL, timeout=8)
        data = r.json().get("data", [{}])[0]
        score = int(data.get("value", 50))
        return {"fear_greed_score": score, "fear_greed_label": _fear_greed_label(score)}
    except Exception as e:
        logger.warning(f"Fear & Greed: {e}")
        return {"fear_greed_score": None, "fear_greed_label": "N/A"}


async def _fetch_funding_rate(client: httpx.AsyncClient) -> str:
    try:
        r = await client.get(BINANCE_FUND_URL, timeout=8)
        data = r.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        rate = float(data.get("lastFundingRate", 0)) * 100
        if rate > 0.05:
            return f"Positifs ({rate:.3f}%) — haussiers"
        elif rate < -0.05:
            return f"Négatifs ({rate:.3f}%) — baissiers"
        else:
            return f"Neutres ({rate:.3f}%)"
    except Exception as e:
        logger.warning(f"Funding rates: {e}")
        return "N/A"


async def collect_dashboard() -> dict:
    """Récupère toutes les données dashboard crypto en parallèle."""
    headers = {"User-Agent": "CORTEX/1.0"}
    async with httpx.AsyncClient(headers=headers) as client:
        global_data, btc_data, fg_data, funding = await asyncio.gather(
            _fetch_coingecko_global(client),
            _fetch_btc_price(client),
            _fetch_fear_greed(client),
            _fetch_funding_rate(client),
        )

    dashboard = {
        **global_data,
        **btc_data,
        **fg_data,
        "funding_description": funding,
    }
    logger.info(
        f"Dashboard crypto: BTC ${dashboard.get('btc_price', 'N/A'):,} "
        f"({dashboard.get('btc_change_24h', '?')}%), "
        f"F&G {dashboard.get('fear_greed_score', '?')}"
    )
    return dashboard


# ── Collecte signaux news ─────────────────────────────────────────────────────

async def _fetch_rss_feed(feed_info: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = []
    try:
        feed = await asyncio.to_thread(feedparser.parse, feed_info["url"])
        for entry in feed.entries[:20]:
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
            if not _is_crypto_relevant(title + " " + content):
                continue

            signals.append({
                "title":       title,
                "source_name": feed_info["name"],
                "source_url":  url,
                "raw_content": content,
                "sector":      "crypto",
                "category":    "media",
            })
    except Exception as e:
        logger.warning(f"Crypto RSS {feed_info['name']}: {e}")
    return signals


async def collect_signals(hours: int = 24) -> list[dict]:
    """Collecte les signaux news crypto depuis tous les flux RSS."""
    results = await asyncio.gather(
        *[_fetch_rss_feed(f, hours) for f in CRYPTO_NEWS_FEEDS],
        return_exceptions=True,
    )
    signals = []
    for r in results:
        if isinstance(r, list):
            signals.extend(r)

    # Déduplication par URL
    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    logger.info(f"SCOUT-CRYPTO signaux: {len(unique)} news ({hours}h)")
    return unique


# ── Point d'entrée principal ──────────────────────────────────────────────────

async def collect(hours: int = 24) -> dict:
    """
    Lance la collecte complète SCOUT-CRYPTO.
    Retourne : {dashboard: dict, signals: list[dict]}
    """
    dashboard, signals = await asyncio.gather(
        collect_dashboard(),
        collect_signals(hours),
    )
    return {"dashboard": dashboard, "signals": signals}
