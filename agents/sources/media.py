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
    "rag", "fine-tun", "reasoning", "multimodal", "o3", "o4", "o1",
    "grok", "xai", "perplexity", "cohere", "databricks", "hugging face",
    "tokens", "context window", "benchmark", "evals", "safety",
]

# Mots-clés qui marquent une annonce majeure (nouveau modèle, partnership, funding)
MAJOR_ANNOUNCEMENT_KEYWORDS = [
    "launches", "announces", "releases", "introduces", "unveils", "partnership",
    "raises", "funding", "billion", "deal", "integrates", "acquire", "acquires",
    "new model", "new version", "update", "breakthrough", "record", "first ever",
    "open source", "open-source", "lancement", "annonce", "partenariat", "accord",
    "nouveau modèle", "levée de fonds", "acquisition",
]

def _tag_signal(title: str, content: str, source_name: str) -> str:
    """Détermine le tag de catégorie du signal pour affichage."""
    text = (title + " " + content + " " + source_name).lower()

    # Blogs officiels → annonce directe
    official_sources = ["openai", "anthropic", "deepmind", "meta ai", "mistral",
                        "google", "xai", "microsoft research", "apple ml", "aws ai"]
    if any(s in source_name.lower() for s in official_sources):
        if any(kw in text for kw in ["launches", "releases", "announces", "new", "update", "lancement"]):
            return "NOUVEAU MODÈLE" if any(m in text for m in ["model", "modèle", "gpt", "claude", "gemini"]) else "ANNONCE OFFICIELLE"
        return "BLOG OFFICIEL"

    if any(kw in text for kw in ["partnership", "deal", "integrates", "partenariat", "accord", "raises", "funding", "billion", "levée"]):
        return "PARTNERSHIP / FUNDING"
    if any(kw in text for kw in ["launches", "releases", "new model", "new version", "nouveau modèle", "lancement"]):
        return "NOUVEAU MODÈLE"
    if any(kw in text for kw in ["research", "paper", "arxiv", "study", "benchmark", "evals"]):
        return "RECHERCHE"
    if "github" in source_name.lower() or "hugging face" in source_name.lower():
        return "GITHUB / HUGGINGFACE"
    if any(r in source_name.lower() for r in ["reddit", "hacker news", "hn"]):
        return "VIRAL COMMUNAUTÉ"
    return "NEWS IA"


# ── Flux RSS ──────────────────────────────────────────────────────────────────
MEDIA_FEEDS = [
    # Médias tech
    {"name": "The Verge AI",           "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "filter": False},
    {"name": "TechCrunch AI",          "url": "https://techcrunch.com/category/artificial-intelligence/feed/",    "filter": False},
    {"name": "VentureBeat AI",         "url": "https://venturebeat.com/category/ai/feed/",                        "filter": False},
    {"name": "Ars Technica",           "url": "https://feeds.arstechnica.com/arstechnica/index",                  "filter": True},
    {"name": "MIT Technology Review AI","url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "filter": False},
    {"name": "Wired AI",               "url": "https://www.wired.com/feed/tag/ai/rss",                            "filter": False},
    # Blogs officiels labs
    {"name": "OpenAI Blog",            "url": "https://openai.com/blog/rss.xml",                                  "filter": False},
    {"name": "Anthropic Blog",         "url": "https://www.anthropic.com/news/rss",                               "filter": False},
    {"name": "Google DeepMind",        "url": "https://deepmind.google/blog/rss.xml",                             "filter": False},
    {"name": "Google AI Blog",         "url": "https://blog.google/technology/ai/rss/",                           "filter": False},
    {"name": "Meta AI Blog",           "url": "https://ai.meta.com/blog/rss.xml",                                 "filter": False},
    {"name": "Mistral AI",             "url": "https://mistral.ai/news/rss",                                      "filter": False},
    {"name": "Microsoft Research AI",  "url": "https://www.microsoft.com/en-us/research/feed/",                   "filter": True},
    {"name": "Apple ML Research",      "url": "https://machinelearning.apple.com/rss.xml",                        "filter": False},
    {"name": "AWS AI Blog",            "url": "https://aws.amazon.com/blogs/machine-learning/feed/",              "filter": False},
    {"name": "Hugging Face Blog",      "url": "https://huggingface.co/blog/feed.xml",                             "filter": False},
    # Newsletters chercheurs
    {"name": "Import AI (Jack Clark)", "url": "https://importai.substack.com/feed",                               "filter": False},
    {"name": "The Rundown AI",         "url": "https://www.therundown.ai/feed",                                   "filter": False},
    {"name": "TLDR AI",                "url": "https://tldr.tech/ai/rss",                                         "filter": False},
    {"name": "Last Week in AI",        "url": "https://lastweekin.ai/feed",                                       "filter": False},
    {"name": "Turing Post",            "url": "https://www.turingpost.com/feed",                                   "filter": False},
    {"name": "BuzzRobot",              "url": "https://buzzrobot.substack.com/feed",                              "filter": False},
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

                tag = _tag_signal(title, content, feed_info["name"])
                signals.append({
                    "sector":      "ai",
                    "category":    "media",
                    "signal_tag":  tag,
                    "source_name": feed_info["name"],
                    "source_url":  url,
                    "title":       title,
                    "raw_content": content[:600] if content else title,
                    "stars_count": 0,
                    "is_major":    any(kw in (title + " " + content[:200]).lower() for kw in MAJOR_ANNOUNCEMENT_KEYWORDS),
                })
                count += 1

            if count:
                logger.info(f"Médias — {feed_info['name']}: {count} articles")

        except Exception as e:
            logger.warning(f"Médias erreur {feed_info['name']}: {e}")

    logger.info(f"Médias TOTAL: {len(signals)} signaux")
    return signals
