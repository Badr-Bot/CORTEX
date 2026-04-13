"""
CORTEX SCOUT-AI — Sources : Comptes X/Twitter des figures clés IA
Surveille via Nitter RSS : @sama, @karpathy, @ylecun, @rowancheung, @_akhaliq
"""

import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.titans")

TITAN_KEYWORDS = [
    "openai", "gpt", "o3", "o4", "anthropic", "claude",
    "deepmind", "gemini", "meta ai", "llama", "mistral",
    "model release", "new model", "training", "alignment",
    "leaked", "benchmark", "agi", "compute", "inference",
    "deepseek", "qwen", "phi", "grok",
]

INFLUENCERS = [
    {"username": "sama",        "name": "Sam Altman"},
    {"username": "karpathy",    "name": "Andrej Karpathy"},
    {"username": "ylecun",      "name": "Yann LeCun"},
    {"username": "rowancheung", "name": "Rowan Cheung"},
    {"username": "_akhaliq",    "name": "AK (@_akhaliq)"},
]

NITTER_INSTANCES = [
    "https://nitter.privacyredirect.com",
    "https://nitter.poast.org",
    "https://nitter.net",
    "https://nitter.1d4.us",
]


def _is_within(entry, hours: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                dt = datetime(*val[:6], tzinfo=timezone.utc)
                return dt >= cutoff
            except Exception:
                pass
    return True


def _has_titan_keyword(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in TITAN_KEYWORDS)


async def fetch_influencers(hours: int = 48) -> list[dict]:
    """Collecte les tweets IA des figures clés via Nitter RSS."""
    signals = []
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        for inf in INFLUENCERS:
            username  = inf["username"]
            collected = False

            for instance in NITTER_INSTANCES:
                rss_url = f"{instance}/{username}/rss"
                try:
                    resp = await client.get(
                        rss_url,
                        headers={"User-Agent": "Mozilla/5.0 CORTEX/2.0"},
                    )
                    if resp.status_code != 200:
                        continue

                    feed  = feedparser.parse(resp.text)
                    count = 0
                    for entry in feed.entries:
                        if not _is_within(entry, hours):
                            continue
                        title = entry.get("title", "").strip()
                        url   = entry.get("link", "").strip()
                        if not title or not _has_titan_keyword(title):
                            continue
                        signals.append({
                            "sector":      "ai",
                            "category":    "titans",
                            "source_name": f"@{username} — {inf['name']}",
                            "source_url":  url,
                            "title":       title[:220],
                            "raw_content": title,
                            "stars_count": 0,
                        })
                        count += 1

                    if count:
                        logger.info(f"Twitter/@{username}: {count} tweets IA")
                    collected = True
                    break

                except Exception as e:
                    logger.debug(f"Nitter {instance}/@{username}: {e}")

            if not collected:
                logger.warning(f"Twitter/@{username} inaccessible via Nitter")

    return signals


async def collect(hours: int = 48) -> list[dict]:
    """Collecte les tweets IA des figures clés."""
    signals = await fetch_influencers(hours)
    logger.info(f"Titans/Twitter TOTAL: {len(signals)} tweets")
    return signals
