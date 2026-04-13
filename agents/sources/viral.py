"""
CORTEX SCOUT-AI — Sources : Signaux Viraux & Trending
Surveille :
  - GitHub Trending (Python, Jupyter Notebook) — repos qui explosent
  - HuggingFace trending (modèles + spaces)
  - Hacker News top stories IA
"""

import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.viral")

HN_AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral",
    "openai", "anthropic", "deepmind", "hugging face",
    "machine learning", "neural", "diffusion", "stable diffusion",
    "chatbot", "agent", "rag", "fine-tun", "transformer",
    "deepseek", "qwen", "phi", "multimodal",
]


def _hours_ago_ts(hours: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())


def _is_ai_related(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in HN_AI_KEYWORDS)


# ── GitHub Trending (Python + Jupyter) ────────────────────────────────────────

async def fetch_github_trending(hours: int = 24) -> list[dict]:
    """
    Repos Python et Jupyter Notebook qui montent vite sur GitHub.
    Utilise la GitHub Search API avec filtre sur création récente + stars.
    """
    signals = []
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max(hours, 24))).strftime("%Y-%m-%d")

    queries = [
        f"language:python stars:>100 pushed:>{cutoff} AI OR LLM OR machine learning",
        f"language:python stars:>200 created:>{cutoff}",
        f"language:jupyter-notebook stars:>50 pushed:>{cutoff}",
    ]

    async with httpx.AsyncClient(
        timeout=15,
        headers={"Accept": "application/vnd.github.v3+json"},
    ) as client:
        for query in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": 8},
                )
                if resp.status_code == 200:
                    for repo in resp.json().get("items", []):
                        desc   = repo.get("description", "") or ""
                        name   = repo.get("full_name", "")
                        stars  = repo.get("stargazers_count", 0)
                        url    = repo.get("html_url", "")
                        lang   = repo.get("language", "")
                        forks  = repo.get("forks_count", 0)

                        if not _is_ai_related(name + " " + desc):
                            continue

                        signals.append({
                            "sector":      "ai",
                            "category":    "viral",
                            "source_name": f"GitHub Trending ({lang})",
                            "source_url":  url,
                            "title":       f"🔥 {name} — {desc[:100]}",
                            "raw_content": (
                                f"Stars: {stars:,} | Forks: {forks:,} | "
                                f"Language: {lang} | {desc}"
                            ),
                            "stars_count": stars,
                        })
                elif resp.status_code == 403:
                    logger.warning("GitHub API rate limit — trending ignoré")
                    break
            except Exception as e:
                logger.warning(f"GitHub trending erreur: {e}")

    # Dédupliquer + trier par stars
    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)
    unique.sort(key=lambda x: x["stars_count"], reverse=True)

    logger.info(f"GitHub Trending: {len(unique)} repos")
    return unique[:15]


# ── GitHub repos établis à forte traction ────────────────────────────────────

async def fetch_github_viral(hours: int = 168) -> list[dict]:
    """Repos IA > 2000 stars récemment actifs — preuve de traction forte."""
    signals = []
    pushed  = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")

    queries = [
        f"AI LLM stars:>3000 pushed:>{pushed}",
        f"language model stars:>3000 pushed:>{pushed}",
        f"AI agent stars:>2000 pushed:>{pushed}",
    ]

    async with httpx.AsyncClient(
        timeout=15,
        headers={"Accept": "application/vnd.github.v3+json"},
    ) as client:
        for query in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": 8},
                )
                if resp.status_code == 200:
                    for repo in resp.json().get("items", []):
                        signals.append({
                            "sector":      "ai",
                            "category":    "viral",
                            "source_name": "GitHub Viral",
                            "source_url":  repo.get("html_url", ""),
                            "title":       f"🔥 {repo['full_name']} — {(repo.get('description') or '')[:100]}",
                            "raw_content": (
                                f"Stars: {repo.get('stargazers_count', 0):,} | "
                                f"Forks: {repo.get('forks_count', 0):,} | "
                                f"{repo.get('description', '')}"
                            ),
                            "stars_count": repo.get("stargazers_count", 0),
                        })
                elif resp.status_code == 403:
                    logger.warning("GitHub API rate limit")
                    break
            except Exception as e:
                logger.warning(f"GitHub viral erreur: {e}")

    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)
    unique.sort(key=lambda x: x["stars_count"], reverse=True)

    logger.info(f"GitHub viral: {len(unique)} repos")
    return unique[:12]


# ── Hugging Face trending ─────────────────────────────────────────────────────

async def fetch_huggingface_trending(limit: int = 15) -> list[dict]:
    """Modèles et Spaces en trending sur HuggingFace."""
    signals = []

    endpoints = [
        {
            "url":    "https://huggingface.co/api/models",
            "params": {"sort": "trendingScore", "direction": "-1", "limit": limit},
            "type":   "model",
        },
        {
            "url":    "https://huggingface.co/api/spaces",
            "params": {"sort": "trendingScore", "direction": "-1", "limit": 10},
            "type":   "space",
        },
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for ep in endpoints:
            try:
                resp = await client.get(ep["url"], params=ep["params"])
                if resp.status_code != 200:
                    continue

                count = 0
                for item in resp.json():
                    model_id = item.get("id", item.get("modelId", ""))
                    if not model_id:
                        continue

                    downloads = item.get("downloads", 0)
                    likes     = item.get("likes", 0)
                    pipeline  = item.get("pipeline_tag", "")
                    trending  = item.get("trendingScore", 0)

                    if ep["type"] == "model":
                        url   = f"https://huggingface.co/{model_id}"
                        title = f"🤗 [{pipeline}] {model_id}"
                        raw   = f"Downloads: {downloads:,} | Likes: {likes:,} | Trending: {trending:.1f}"
                    else:
                        url   = f"https://huggingface.co/spaces/{model_id}"
                        title = f"🤗 Space: {model_id}"
                        raw   = f"Likes: {likes:,} | Trending: {trending:.1f}"

                    signals.append({
                        "sector":      "ai",
                        "category":    "viral",
                        "source_name": f"HuggingFace ({ep['type']}s)",
                        "source_url":  url,
                        "title":       title,
                        "raw_content": raw,
                        "stars_count": likes,
                    })
                    count += 1

                logger.info(f"HuggingFace {ep['type']}s: {count}")
            except Exception as e:
                logger.warning(f"HuggingFace {ep['type']} erreur: {e}")

    return signals


# ── Hacker News ───────────────────────────────────────────────────────────────

async def fetch_hacker_news(hours: int = 48) -> list[dict]:
    """Top stories IA sur Hacker News via Algolia."""
    signals = []
    cutoff  = _hours_ago_ts(hours)
    queries = ["AI LLM", "OpenAI Anthropic", "machine learning model", "AI agent autonomous"]

    async with httpx.AsyncClient(timeout=15) as client:
        for q in queries:
            try:
                resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={
                        "tags":           "story",
                        "query":          q,
                        "numericFilters": f"created_at_i>{cutoff},points>50",
                        "hitsPerPage":    8,
                    },
                )
                if resp.status_code != 200:
                    continue

                for hit in resp.json().get("hits", []):
                    title  = hit.get("title", "").strip()
                    url    = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                    points = hit.get("points", 0)

                    if not title or not _is_ai_related(title):
                        continue

                    signals.append({
                        "sector":      "ai",
                        "category":    "viral",
                        "source_name": "Hacker News",
                        "source_url":  url,
                        "title":       f"🔺 {title}",
                        "raw_content": f"Points: {points} | Comments: {hit.get('num_comments', 0)}",
                        "stars_count": points,
                    })
            except Exception as e:
                logger.warning(f"HN erreur '{q}': {e}")

    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)
    unique.sort(key=lambda x: x["stars_count"], reverse=True)

    logger.info(f"Hacker News: {len(unique)} stories IA")
    return unique[:12]


# ── Point d'entrée ────────────────────────────────────────────────────────────

async def collect(hours: int = 48) -> list[dict]:
    """Collecte tous les signaux viraux."""
    import asyncio
    trending, viral, hf, hn = await asyncio.gather(
        fetch_github_trending(hours),
        fetch_github_viral(hours),
        fetch_huggingface_trending(),
        fetch_hacker_news(hours),
        return_exceptions=True,
    )

    def _safe(r, n):
        if isinstance(r, Exception):
            logger.error(f"Collect {n} échoué: {r}")
            return []
        return r

    trending = _safe(trending, "GitHub trending")
    viral    = _safe(viral,    "GitHub viral")
    hf       = _safe(hf,       "HuggingFace")
    hn       = _safe(hn,       "Hacker News")

    total = trending + viral + hf + hn
    logger.info(
        f"Viral TOTAL: {len(total)} "
        f"({len(trending)} trending, {len(viral)} viral, {len(hf)} HF, {len(hn)} HN)"
    )
    return total
