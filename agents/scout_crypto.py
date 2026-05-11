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
FEAR_GREED_URL   = "https://api.alternative.me/fng/?limit=7"
BINANCE_FUND_URL = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
BINANCE_OI_URL   = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
BINANCE_LS_URL   = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1"
MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
COINGLASS_LIQ_URL = "https://open-api.coinglass.com/public/v2/liquidation_history"

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
    """Triple fallback : CoinGecko → Binance → CryptoCompare."""
    # Source 1 : CoinGecko
    try:
        r = await client.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10,
        )
        if r.status_code == 200:
            btc = r.json().get("bitcoin", {})
            price = btc.get("usd", 0)
            if price > 0:
                return {
                    "btc_price":      price,
                    "btc_change_24h": round(btc.get("usd_24h_change", 0), 1),
                    "btc_price_source": "CoinGecko",
                }
    except Exception:
        pass

    # Source 2 : Binance (fallback)
    try:
        r = await client.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": "BTCUSDT"}, timeout=8,
        )
        if r.status_code == 200:
            d = r.json()
            price = float(d.get("lastPrice", 0))
            prev  = float(d.get("prevClosePrice", price))
            change = round((price - prev) / prev * 100, 1) if prev else 0
            if price > 0:
                return {
                    "btc_price":      int(price),
                    "btc_change_24h": change,
                    "btc_price_source": "Binance",
                }
    except Exception:
        pass

    # Source 3 : CryptoCompare (fallback ultime)
    try:
        r = await client.get(
            "https://min-api.cryptocompare.com/data/price",
            params={"fsym": "BTC", "tsyms": "USD"}, timeout=8,
        )
        if r.status_code == 200:
            price = r.json().get("USD", 0)
            if price > 0:
                return {
                    "btc_price":      int(price),
                    "btc_change_24h": 0,
                    "btc_price_source": "CryptoCompare",
                }
    except Exception:
        pass

    logger.error("BTC price: toutes les sources ont échoué")
    return {"btc_price": 0, "btc_change_24h": 0, "btc_price_source": "N/A"}


async def _fetch_fear_greed(client: httpx.AsyncClient) -> dict:
    """Fear & Greed actuel + tendance 7 jours."""
    try:
        r = await client.get(FEAR_GREED_URL, timeout=8)
        data = r.json().get("data", [{}])
        if not data:
            raise ValueError("empty")
        score = int(data[0].get("value", 50))
        # Tendance 7j
        scores_7d = [int(d.get("value", 50)) for d in data[:7]]
        trend = "en hausse" if scores_7d[0] > scores_7d[-1] else "en baisse" if scores_7d[0] < scores_7d[-1] else "stable"
        avg_7d = round(sum(scores_7d) / len(scores_7d))
        return {
            "fear_greed_score": score,
            "fear_greed_label": _fear_greed_label(score),
            "fear_greed_trend": trend,
            "fear_greed_avg_7d": avg_7d,
        }
    except Exception as e:
        logger.warning(f"Fear & Greed: {e}")
        return {"fear_greed_score": None, "fear_greed_label": "N/A", "fear_greed_trend": "N/A", "fear_greed_avg_7d": None}


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


async def _fetch_liquidations(client: httpx.AsyncClient) -> dict:
    """Liquidations BTC 24h via Coinglass public endpoint."""
    try:
        r = await client.get(
            "https://open-api.coinglass.com/public/v2/liquidation",
            params={"ex": "Binance", "pair": "BTCUSDT", "interval": "0"},
            timeout=8,
            headers={"accept": "application/json"},
        )
        if r.status_code == 200:
            d = r.json().get("data", {})
            longs  = d.get("longLiquidationUsd24h", 0) or 0
            shorts = d.get("shortLiquidationUsd24h", 0) or 0
            return {
                "liq_longs_24h_usd":  int(longs),
                "liq_shorts_24h_usd": int(shorts),
                "liq_dominance": "shorts" if shorts > longs * 1.5 else "longs" if longs > shorts * 1.5 else "équilibré",
            }
    except Exception:
        pass
    # Fallback : Coinglass alternatif
    try:
        r = await client.get(
            "https://fapi.binance.com/fapi/v1/forceOrders",
            params={"symbol": "BTCUSDT", "autoCloseType": "LIQUIDATION", "limit": 100},
            timeout=8,
        )
        if r.status_code == 200:
            orders = r.json()
            longs = sum(float(o.get("origQty", 0)) * float(o.get("price", 0))
                        for o in orders if o.get("side") == "SELL")
            shorts = sum(float(o.get("origQty", 0)) * float(o.get("price", 0))
                         for o in orders if o.get("side") == "BUY")
            return {
                "liq_longs_24h_usd":  int(longs),
                "liq_shorts_24h_usd": int(shorts),
                "liq_dominance": "shorts" if shorts > longs * 1.5 else "longs" if longs > shorts * 1.5 else "équilibré",
            }
    except Exception as e:
        logger.debug(f"Liquidations: {e}")
    return {"liq_longs_24h_usd": 0, "liq_shorts_24h_usd": 0, "liq_dominance": "N/A"}


def _detect_btc_cycle(btc_price: float, fg_score: int, btc_change_24h: float,
                       funding_desc: str, long_short_ratio: float) -> dict:
    """
    Détecte la phase de cycle BTC avec règles simples mais fiables.
    Phases : Accumulation → Markup → Distribution → Markdown
    """
    score = 0  # positif = bull, négatif = bear

    # Fear & Greed
    if fg_score is not None:
        if fg_score >= 75:   score += 2   # Avidité extrême → distribution
        elif fg_score >= 55: score += 1   # Avidité → markup
        elif fg_score <= 25: score -= 2   # Peur extrême → accumulation/markdown
        elif fg_score <= 45: score -= 1   # Peur → accumulation

    # Momentum prix
    if btc_change_24h >= 5:    score += 1
    elif btc_change_24h <= -5: score -= 1

    # Funding rates
    if funding_desc and "haussiers" in funding_desc:  score += 1
    elif funding_desc and "baissiers" in funding_desc: score -= 1

    # Long/Short ratio
    if long_short_ratio:
        if long_short_ratio > 0.6:  score += 1   # majorité longs = tendance haussière
        elif long_short_ratio < 0.4: score -= 1  # majorité shorts = pression baissière

    # Détermination phase
    if score >= 3:
        phase = "Distribution"
        emoji = "🔴"
        conseil = "Réduction des positions recommandée — euphorie détectée"
    elif score >= 1:
        phase = "Markup"
        emoji = "🟢"
        conseil = "Phase haussière active — tenir ou ajouter sur replis"
    elif score >= -1:
        phase = "Transition"
        emoji = "🟡"
        conseil = "Phase indécise — attendre confirmation de direction"
    elif score >= -3:
        phase = "Accumulation"
        emoji = "🟡"
        conseil = "Zone d'accumulation — DCA progressif possible"
    else:
        phase = "Markdown"
        emoji = "🔴"
        conseil = "Phase baissière — protéger le capital, éviter les achats précipités"

    return {"phase": phase, "emoji": emoji, "conseil": conseil, "cycle_score": score}


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
        global_data, btc_data, fg_data, funding, oi_data, ls_data, mempool_data, liq_data = await asyncio.gather(
            _fetch_coingecko_global(client),
            _fetch_btc_price(client),
            _fetch_fear_greed(client),
            _fetch_funding_rate(client),
            _fetch_open_interest(client),
            _fetch_long_short(client),
            _fetch_mempool_fees(client),
            _fetch_liquidations(client),
        )

    exchange_flows = await collect_exchange_flows()

    dashboard = {
        **global_data,
        **btc_data,
        **fg_data,
        **oi_data,
        **ls_data,
        **mempool_data,
        **liq_data,
        "funding_description": funding,
        "exchange_flows": exchange_flows,
    }

    # Analyse de cycle BTC
    cycle = _detect_btc_cycle(
        btc_price=dashboard.get("btc_price", 0),
        fg_score=dashboard.get("fear_greed_score"),
        btc_change_24h=dashboard.get("btc_change_24h", 0),
        funding_desc=dashboard.get("funding_description", ""),
        long_short_ratio=dashboard.get("long_short_ratio"),
    )
    dashboard["cycle"] = cycle

    logger.info(
        f"Dashboard crypto: BTC ${dashboard.get('btc_price', 'N/A'):,} "
        f"[{dashboard.get('btc_price_source', '?')}] "
        f"({dashboard.get('btc_change_24h', '?')}%), "
        f"F&G {dashboard.get('fear_greed_score', '?')}, "
        f"Cycle: {cycle['phase']}, "
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
