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

COINGECKO_BASE   = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL   = "https://api.alternative.me/fng/?limit=1"
BINANCE_FUND_URL = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
BINANCE_OI_URL   = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
BINANCE_LS_URL   = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1"
MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"

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


async def _fetch_open_interest(client: httpx.AsyncClient) -> dict:
    """Open Interest BTC sur Binance Futures (gratuit, sans clé)."""
    try:
        r    = await client.get(BINANCE_OI_URL, timeout=8)
        data = r.json()
        oi   = float(data.get("openInterest", 0))
        btc_price_approx = 80000  # approximation fallback
        return {"open_interest_btc": oi * btc_price_approx}
    except Exception as e:
        logger.debug(f"Open Interest: {e}")
        return {}


async def _fetch_long_short(client: httpx.AsyncClient) -> dict:
    """Ratio Long/Short global BTC sur Binance (gratuit, sans clé)."""
    try:
        r    = await client.get(BINANCE_LS_URL, timeout=8)
        data = r.json()
        row  = data[0] if isinstance(data, list) and data else {}
        ls   = float(row.get("longShortRatio", 1.0))
        long_pct = ls / (1 + ls)
        return {"long_short_ratio": long_pct}
    except Exception as e:
        logger.debug(f"Long/Short ratio: {e}")
        return {}


async def _fetch_mempool_fees(client: httpx.AsyncClient) -> dict:
    """Frais Bitcoin recommandés (activité on-chain) via mempool.space."""
    try:
        r    = await client.get(MEMPOOL_FEES_URL, timeout=8)
        data = r.json()
        fee  = data.get("halfHourFee", 0)
        return {"mempool_fee": fee}
    except Exception as e:
        logger.debug(f"Mempool fees: {e}")
        return {}


async def collect_exchange_flows() -> dict:
    """
    Estime les flux d'échanges crypto (accumulation vs distribution) via :
    - Volume Binance 24h (tendance achat/vente)
    - Top exchanges volume CoinGecko
    - Heuristique : volume élevé + prix monte → accumulation ; volume élevé + prix baisse → distribution
    """
    result = {
        "binance_vol_24h_usd": 0,
        "top5_exchanges_vol_btc": 0.0,
        "trend": "inconnu",
        "pression": "neutre",
    }
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            binance_r, gecko_r = await asyncio.gather(
                client.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=8),
                client.get(
                    "https://api.coingecko.com/api/v3/exchanges",
                    params={"per_page": 5, "page": 1}, timeout=10,
                ),
                return_exceptions=True,
            )

        # Binance volume
        binance_vol_usd = 0
        if not isinstance(binance_r, Exception) and binance_r.status_code == 200:
            bd = binance_r.json()
            binance_vol_usd = float(bd.get("quoteVolume", 0))
            btc_change = float(bd.get("priceChangePercent", 0))
            result["binance_vol_24h_usd"] = int(binance_vol_usd)
            result["btc_change_24h_pct"] = round(btc_change, 2)
        else:
            btc_change = 0.0

        # CoinGecko top exchanges
        top5_vol = 0.0
        if not isinstance(gecko_r, Exception) and gecko_r.status_code == 200:
            exchanges = gecko_r.json()
            top5_vol = sum(float(ex.get("trade_volume_24h_btc", 0) or 0) for ex in exchanges[:5])
            result["top5_exchanges_vol_btc"] = round(top5_vol, 1)

        # Heuristique flux : volume élevé + prix monte = acheteurs agressifs (accumulation)
        # Volume élevé + prix baisse = vendeurs agressifs (distribution)
        # Volume faible = pas de signal fort
        high_volume_threshold = 800_000_000  # $800M Binance 24h = "élevé"
        if binance_vol_usd > high_volume_threshold:
            if btc_change > 1.0:
                result["trend"] = "accumulation"
                result["pression"] = "achat"
            elif btc_change < -1.0:
                result["trend"] = "distribution"
                result["pression"] = "vente"
            else:
                result["trend"] = "indecis"
                result["pression"] = "neutre"
        else:
            result["trend"] = "faible_volume"
            result["pression"] = "neutre"

        logger.info(
            f"Exchange flows: Binance ${result['binance_vol_24h_usd']:,} | "
            f"BTC {result.get('btc_change_24h_pct', '?')}% | "
            f"Trend: {result['trend']}"
        )
    except Exception as e:
        logger.warning(f"collect_exchange_flows erreur: {e}")

    return result


async def collect_dashboard() -> dict:
    """Récupère toutes les données dashboard crypto en parallèle."""
    headers = {"User-Agent": "CORTEX/1.0"}
    async with httpx.AsyncClient(headers=headers) as client:
        global_data, btc_data, fg_data, funding, oi_data, ls_data, mempool_data = await asyncio.gather(
            _fetch_coingecko_global(client),
            _fetch_btc_price(client),
            _fetch_fear_greed(client),
            _fetch_funding_rate(client),
            _fetch_open_interest(client),
            _fetch_long_short(client),
            _fetch_mempool_fees(client),
        )

    exchange_flows = await collect_exchange_flows()

    dashboard = {
        **global_data,
        **btc_data,
        **fg_data,
        **oi_data,
        **ls_data,
        **mempool_data,
        "funding_description": funding,
        "exchange_flows": exchange_flows,
    }
    logger.info(
        f"Dashboard crypto: BTC ${dashboard.get('btc_price', 'N/A'):,} "
        f"({dashboard.get('btc_change_24h', '?')}%), "
        f"F&G {dashboard.get('fear_greed_score', '?')}, "
        f"Flows: {exchange_flows.get('trend', '?')}"
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
