"""
CORTEX — Récupération RSS robuste.

Pourquoi ce module : `feedparser.parse(url)` fait sa propre requête avec un
User-Agent "feedparser". Plusieurs sources (Bitcoinist, NewsBTC, Modern Retail,
Digital Commerce 360...) renvoient 403 ou une page vide à ce User-Agent, alors
qu'elles répondent normalement à un navigateur. Résultat : des flux comptés
comme "vivants" mais qui rendaient 0 article.

On passe donc par httpx avec un User-Agent navigateur, puis on donne les octets
à feedparser. Bonus : on maîtrise le timeout et les redirections.
"""

import asyncio
from datetime import datetime, timezone, timedelta

import feedparser
import httpx

from utils.logger import get_logger

logger = get_logger("feeds")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


async def fetch_feed(url: str, timeout: int = 15):
    """Télécharge un flux avec un User-Agent navigateur et le parse."""
    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=timeout, follow_redirects=True
        ) as client:
            r = await client.get(url)
        if r.status_code != 200:
            logger.warning(f"Flux {url} → HTTP {r.status_code}")
            return None
        return await asyncio.to_thread(feedparser.parse, r.content)
    except Exception as e:
        logger.warning(f"Flux {url} échoué: {type(e).__name__} {str(e)[:100]}")
        return None


def entry_date(entry) -> datetime | None:
    """Date de publication d'une entrée, en UTC."""
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    if not pub:
        return None
    try:
        return datetime(*pub[:6], tzinfo=timezone.utc)
    except Exception:
        return None


async def collect_feed_entries(
    feed_info: dict,
    hours: int,
    sector: str,
    is_relevant=None,
    max_entries: int = 20,
    keep_undated: bool = True,
) -> list[dict]:
    """
    Récupère les entrées récentes d'un flux et les normalise au format signal CORTEX.

    feed_info    : {"name": str, "url": str}
    is_relevant  : fonction (texte) -> bool, filtre thématique optionnel
    keep_undated : garder les entrées sans date (certains flux n'en publient pas)
    """
    feed = await fetch_feed(feed_info["url"])
    if feed is None:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = []

    for entry in feed.entries[:max_entries]:
        pub_dt = entry_date(entry)
        if pub_dt is None:
            if not keep_undated:
                continue
        elif pub_dt < cutoff:
            continue

        title = (entry.get("title") or "").strip()
        url = entry.get("link") or ""
        content = (entry.get("summary") or entry.get("description") or "")[:400]

        if not title or not url:
            continue
        if is_relevant and not is_relevant(f"{title} {content}"):
            continue

        signals.append({
            "title":       title,
            "source_name": feed_info["name"],
            "source_url":  url,
            "raw_content": content,
            "sector":      sector,
            "category":    "media",
        })

    return signals


async def collect_from_feeds(
    feeds: list[dict],
    hours: int,
    sector: str,
    is_relevant=None,
    max_entries: int = 20,
) -> list[dict]:
    """Collecte parallèle sur une liste de flux, dédupliquée par URL."""
    results = await asyncio.gather(
        *[
            collect_feed_entries(f, hours, sector, is_relevant, max_entries)
            for f in feeds
        ],
        return_exceptions=True,
    )

    signals = []
    for r in results:
        if isinstance(r, list):
            signals.extend(r)

    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    return unique
