"""
CORTEX SCOUT-AI — Sources : Médias, Blogs & Newsletters IA
Surveille les grands médias tech + blogs officiels + newsletters chercheurs
via leurs flux RSS.
"""

import feedparser
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.media")

AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "gpt", "claude", "gemini", "llama",
    "openai", "anthropic", "deepmind", "meta ai", "mistral",
    "chatgpt", "copilot", "neural", "transformer", "diffusion",
    "image generation", "foundation model", "autonomous", "agent",
    "rag", "fine-tun", "reasoning", "multimodal",
]

# ── Flux RSS ──────────────────────────────────────────────────────────────────
MEDIA_FEEDS = [
    # Médias tech
    {
        "name":   "The Verge AI",
        "url":    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "filter": False,
    },
    {
        "name":   "TechCrunch AI",
        "url":    "https://techcrunch.com/category/artificial-intelligence/feed/",
        "filter": False,
    },
    {
        "name":   "VentureBeat AI",
        "url":    "https://venturebeat.com/category/ai/feed/",
        "filter": False,
    },
    {
        "name":   "Ars Technica",
        "url":    "https://feeds.arstechnica.com/arstechnica/index",
        "filter": True,   # fil généraliste → filtrer par mot-clé IA
    },
    {
        "name":   "MIT Technology Review AI",
        "url":    "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "filter": False,
    },
    {
        "name":   "Wired AI",
        "url":    "https://www.wired.com/feed/tag/ai/rss",
        "filter": False,
    },
    # Blogs officiels
    {
        "name":   "OpenAI Blog",
        "url":    "https://openai.com/blog/rss.xml",
        "filter": False,
    },
    {
        "name":   "Anthropic Blog",
        "url":    "https://www.anthropic.com/news/rss",
        "filter": False,
    },
    {
        "name":   "Google DeepMind",
        "url":    "https://deepmind.google/blog/rss.xml",
        "filter": False,
    },
    {
        "name":   "Meta AI Blog",
        "url":    "https://ai.meta.com/blog/rss.xml",
        "filter": False,
    },
    {
        "name":   "Mistral AI",
        "url":    "https://mistral.ai/news/rss",
        "filter": False,
    },
    # Newsletters chercheurs
    {
        "name":   "Import AI (Jack Clark)",
        "url":    "https://importai.substack.com/feed",
        "filter": False,
    },
    {
        "name":   "BuzzRobot",
        "url":    "https://buzzrobot.substack.com/feed",
        "filter": False,
    },
    {
        "name":   "Turing Post",
        "url":    "https://www.turingpost.com/feed",
        "filter": False,
    },
    {
        "name":   "TLDR AI",
        "url":    "https://tldr.tech/ai/rss",
        "filter": False,
    },
    {
        "name":   "The Rundown AI",
        "url":    "https://www.therundown.ai/feed",
        "filter": False,
    },
    {
        "name":   "Last Week in AI",
        "url":    "https://lastweekin.ai/feed",
        "filter": False,
    },
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
    return True  # Pas de date → inclus par défaut


def _is_ai_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AI_KEYWORDS)


async def collect(hours: int = 48) -> list[dict]:
    """Collecte les articles IA des médias, blogs officiels et newsletters."""
    signals = []

    for feed_info in MEDIA_FEEDS:
        try:
            feed  = feedparser.parse(feed_info["url"])
            count = 0

            for entry in feed.entries:
                if not _is_within(entry, hours):
                    continue

                title   = entry.get("title", "").strip()
                url     = entry.get("link", "").strip()
                content = entry.get("summary", entry.get("description", ""))

                if not title or not url:
                    continue

                # Filtrer par mot-clé IA si nécessaire
                if feed_info.get("filter"):
                    if not _is_ai_relevant(title + " " + content[:200]):
                        continue

                signals.append({
                    "sector":      "ai",
                    "category":    "media",
                    "source_name": feed_info["name"],
                    "source_url":  url,
                    "title":       title,
                    "raw_content": content[:600] if content else title,
                    "stars_count": 0,
                })
                count += 1

            if count:
                logger.info(f"Médias — {feed_info['name']}: {count} articles")

        except Exception as e:
            logger.warning(f"Médias erreur {feed_info['name']}: {e}")

    logger.info(f"Médias TOTAL: {len(signals)} signaux")
    return signals
