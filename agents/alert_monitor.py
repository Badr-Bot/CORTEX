"""
CORTEX — Agent ALERT-MONITOR v2
Surveille les marchés ET les breaking news en temps réel.
Cooldown stocké en Supabase (persiste entre les runs GitHub Actions).

Marchés : VIX +20%, BTC ±10%, S&P -3%, Or +3%, DXY +1.5%
News     : Reuters, BBC, CNBC, MarketWatch, CoinDesk
Scoring  : Groq Llama 3.3 gratuit — seuil 9/10 pour alerte
"""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone, timedelta

import feedparser
import httpx

from utils.logger import get_logger

logger = get_logger("alert_monitor")

# ── Seuils marchés ────────────────────────────────────────────
MARKET_THRESHOLDS = {
    "vix_spike":   {"label": "VIX SPIKE",  "emoji": "🔥", "cooldown_h": 2},
    "btc_crash":   {"label": "BTC CRASH",  "emoji": "🚨", "cooldown_h": 2},
    "btc_rally":   {"label": "BTC RALLY",  "emoji": "🚀", "cooldown_h": 2},
    "sp500_chute": {"label": "S&P CHUTE",  "emoji": "📉", "cooldown_h": 2},
    "or_refuge":   {"label": "OR REFUGE",  "emoji": "🥇", "cooldown_h": 4},
    "dxy_spike":   {"label": "DXY SPIKE",  "emoji": "💵", "cooldown_h": 4},
}

# ── Sources RSS breaking news ─────────────────────────────────
NEWS_FEEDS = [
    {"name": "Reuters",     "url": "https://feeds.reuters.com/reuters/topNews",                                           "cooldown_h": 6},
    {"name": "BBC",         "url": "https://feeds.bbci.co.uk/news/rss.xml",                                               "cooldown_h": 6},
    {"name": "CNBC",        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "cooldown_h": 6},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/",                               "cooldown_h": 6},
    {"name": "CoinDesk",    "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",                                     "cooldown_h": 4},
]

URGENT_KEYWORDS = [
    # Géopolitique
    "war", "attack", "invasion", "missile", "nuclear", "explosion", "coup",
    "assassination", "troops", "conflict", "strike", "bombing", "guerre",
    "attaque", "missile", "nucléaire",
    # Marchés / crise
    "crash", "circuit breaker", "emergency", "halt", "suspended", "default",
    "bankruptcy", "bailout", "collapse", "panic", "crisis", "krach",
    # Macro / Fed
    "rate hike", "rate cut", "emergency meeting", "fed raises", "fed cuts",
    "inflation surge", "recession", "powell", "lagarde", "ecb decision",
    # Crypto
    "hack", "exploit", "exchange collapse", "sec ban", "regulatory ban",
    "binance", "coinbase sued", "bitcoin etf", "crypto ban",
    # IA / tech
    "gpt-5", "gpt5", "claude 4", "gemini ultra", "agi", "major breakthrough",
    "openai", "deepmind",
]


# ── Cooldown Supabase ─────────────────────────────────────────

def _is_in_cooldown(key: str, hours: int) -> bool:
    try:
        from database.client import get_supabase_client
        client = get_supabase_client()
        result = client.table("alert_cooldowns").select("last_sent").eq("key", key).execute()
        if not result.data:
            return False
        last = datetime.fromisoformat(result.data[0]["last_sent"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last < timedelta(hours=hours)
    except Exception as e:
        logger.debug(f"Cooldown check error ({key}): {e}")
        return False


def _set_cooldown(key: str) -> None:
    try:
        from database.client import get_supabase_client
        client = get_supabase_client()
        client.table("alert_cooldowns").upsert({
            "key": key,
            "last_sent": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Impossible de sauver cooldown ({key}): {e}")


def _news_key(url: str) -> str:
    return "news_" + hashlib.md5(url.encode()).hexdigest()[:12]


# ── Données marché ────────────────────────────────────────────

async def _fetch_market_snapshot() -> dict:
    snapshot = {}
    headers = {"User-Agent": "Mozilla/5.0"}

    async def _get(client: httpx.AsyncClient, key: str, symbol: str) -> None:
        try:
            r = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "5d"}, timeout=8,
            )
            if r.status_code != 200:
                return
            meta = r.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice") or 0
            prev  = meta.get("chartPreviousClose") or meta.get("regularMarketPreviousClose") or price
            change = round((price - prev) / prev * 100, 2) if prev else 0
            snapshot[key] = {"price": price, "change_pct": change}
        except Exception as e:
            logger.debug(f"Market fetch {symbol}: {e}")

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        await asyncio.gather(
            _get(client, "vix",   "^VIX"),
            _get(client, "sp500", "^GSPC"),
            _get(client, "gold",  "GC=F"),
            _get(client, "dxy",   "DX-Y.NYB"),
        )

    try:
        async with httpx.AsyncClient(headers={"User-Agent": "CORTEX/2.0"}) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=8,
            )
            btc = r.json().get("bitcoin", {})
            snapshot["btc"] = {
                "price":      btc.get("usd", 0),
                "change_pct": round(btc.get("usd_24h_change", 0), 2),
            }
    except Exception as e:
        logger.debug(f"BTC fetch: {e}")

    return snapshot


# ── Scoring Groq ──────────────────────────────────────────────

async def _score_and_translate_groq(title: str, summary: str) -> tuple[int, str, str]:
    """Retourne (score, titre_fr, résumé_fr). Score 0 si erreur."""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = (
            "Tu es un analyste macro senior. Évalue cette news et réponds en JSON strict.\n\n"
            "Critères de score :\n"
            "9-10 : conséquences macro/micro CERTAINES (guerre déclarée, crash -5%, décision Fed surprise, "
            "défaut souverain, hack exchange majeur, résultats trimestriels qui changent tout)\n"
            "7-8  : important mais attendu ou incertain\n"
            "1-6  : news ordinaire, politique mineure, rumeur\n\n"
            f"Titre : {title}\n"
            f"Résumé : {summary[:400] if summary else 'N/A'}\n\n"
            'Réponds UNIQUEMENT avec ce JSON (pas de markdown) :\n'
            '{"score": 8, "titre_fr": "...", "resume_fr": "..."}'
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return int(data.get("score", 0)), data.get("titre_fr", title), data.get("resume_fr", "")
    except Exception as e:
        logger.debug(f"Groq score+translate error: {e}")
        return 0, "", ""


# ── Fetch RSS ─────────────────────────────────────────────────

async def _fetch_feed_entries(feed: dict) -> list[dict]:
    """Retourne les entrées récentes (<2h) d'un feed RSS."""
    try:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, feedparser.parse, feed["url"])
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        entries = []
        for e in parsed.entries[:20]:
            published = None
            if hasattr(e, "published_parsed") and e.published_parsed:
                ts = time.mktime(e.published_parsed)
                published = datetime.fromtimestamp(ts, tz=timezone.utc)
            if published and published < cutoff:
                continue
            entries.append({
                "title":      e.get("title", ""),
                "summary":    e.get("summary", ""),
                "url":        e.get("link", ""),
                "source":     feed["name"],
                "cooldown_h": feed["cooldown_h"],
            })
        return entries
    except Exception as e:
        logger.debug(f"Feed fetch {feed['name']}: {e}")
        return []


def _has_urgent_keyword(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in URGENT_KEYWORDS)


# ── Messages Telegram ─────────────────────────────────────────

def _market_alert_msg(key: str, snapshot: dict) -> str:
    cfg = MARKET_THRESHOLDS[key]
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    vix  = snapshot.get("vix",   {})
    sp   = snapshot.get("sp500", {})
    btc  = snapshot.get("btc",   {})
    gold = snapshot.get("gold",  {})
    dxy  = snapshot.get("dxy",   {})

    lines = [f"{cfg['emoji']} *CORTEX — {cfg['label']}* ({now})"]
    if "vix"   in key: lines.append(f"VIX : {vix.get('price', 0):.1f} ({vix.get('change_pct', 0):+.1f}%)")
    if "btc"   in key: lines.append(f"BTC : ${btc.get('price', 0):,.0f} ({btc.get('change_pct', 0):+.1f}%)")
    if "sp500" in key: lines.append(f"S&P 500 : {sp.get('price', 0):,.0f} ({sp.get('change_pct', 0):+.1f}%)")
    if "or"    in key: lines.append(f"Or : ${gold.get('price', 0):,.0f} ({gold.get('change_pct', 0):+.1f}%)")
    if "dxy"   in key: lines.append(f"DXY : {dxy.get('price', 0):.2f} ({dxy.get('change_pct', 0):+.1f}%)")

    lines.append(
        f"\n📊 Marché complet : BTC {btc.get('change_pct', 0):+.1f}% | "
        f"S&P {sp.get('change_pct', 0):+.1f}% | VIX {vix.get('price', 0):.0f}"
    )
    return "\n".join(lines)


def _news_alert_msg(entry: dict, score: int, titre_fr: str, resume_fr: str) -> str:
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    lines = [
        f"🔴 *BREAKING — {entry['source']}* ({now})",
        f"*{titre_fr}*",
    ]
    if resume_fr:
        lines.append(f"\n_{resume_fr}_")
    if entry["url"]:
        lines.append(f"\n🔗 {entry['url']}")
    return "\n".join(lines)


# ── Point d'entrée ────────────────────────────────────────────

async def check_and_send_alerts() -> list[str]:
    sent = []

    try:
        from tgbot.bot import send_message

        # ── 1. Alertes marchés ────────────────────────────────
        snapshot = await _fetch_market_snapshot()

        vix_c  = snapshot.get("vix",   {}).get("change_pct", 0)
        btc_c  = snapshot.get("btc",   {}).get("change_pct", 0)
        sp_c   = snapshot.get("sp500", {}).get("change_pct", 0)
        gold_c = snapshot.get("gold",  {}).get("change_pct", 0)
        dxy_c  = snapshot.get("dxy",   {}).get("change_pct", 0)

        market_triggers = {
            "vix_spike":   vix_c  >= 20,
            "btc_crash":   btc_c  <= -10,
            "btc_rally":   btc_c  >= 10,
            "sp500_chute": sp_c   <= -3,
            "or_refuge":   gold_c >= 3,
            "dxy_spike":   dxy_c  >= 1.5,
        }

        for key, triggered in market_triggers.items():
            if not triggered:
                continue
            cfg = MARKET_THRESHOLDS[key]
            if _is_in_cooldown(key, cfg["cooldown_h"]):
                continue
            msg = _market_alert_msg(key, snapshot)
            await send_message(msg, parse_mode="Markdown")
            _set_cooldown(key)
            sent.append(key)
            logger.info(f"Alerte marché envoyée : {key}")

        logger.info(
            f"Marchés : BTC {btc_c:+.1f}% | S&P {sp_c:+.1f}% | "
            f"VIX {vix_c:+.1f}% | Alertes : {sent or 'aucune'}"
        )

        # ── 2. Breaking news RSS ──────────────────────────────
        all_entries = []
        feed_results = await asyncio.gather(*[_fetch_feed_entries(f) for f in NEWS_FEEDS])
        for entries in feed_results:
            all_entries.extend(entries)

        for entry in all_entries:
            if not entry["url"] or not entry["title"]:
                continue
            if not _has_urgent_keyword(entry["title"], entry["summary"]):
                continue

            news_key = _news_key(entry["url"])
            if _is_in_cooldown(news_key, entry["cooldown_h"]):
                continue

            score, titre_fr, resume_fr = await _score_and_translate_groq(entry["title"], entry["summary"])
            if score < 9:
                logger.debug(f"News score {score}/10 — ignorée : {entry['title'][:60]}")
                continue

            msg = _news_alert_msg(entry, score, titre_fr, resume_fr)
            try:
                await send_message(msg, parse_mode="Markdown")
                _set_cooldown(news_key)
                sent.append(f"news:{entry['source']}")
                logger.info(f"Breaking news envoyée ({score}/10) : {entry['title'][:60]}")
            except Exception as e:
                logger.error(f"Erreur envoi news: {e}")

    except Exception as e:
        logger.error(f"check_and_send_alerts erreur: {e}")

    return sent
