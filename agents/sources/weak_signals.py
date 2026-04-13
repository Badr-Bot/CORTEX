"""
CORTEX SCOUT-AI — Sources : Signaux Faibles & Recherche
Surveille :
  - arXiv (cs.AI, cs.LG, cs.CL, cs.CV)
  - Repos GitHub spécifiques : dair-ai/ML-Papers-of-the-Week,
    deepseek-ai/DeepSeek-V3, ollama/ollama (releases + commits)
  - GitHub — repos IA récents à forte vélocité (<500 stars)
  - Reddit : r/MachineLearning, r/LocalLLaMA, r/artificial,
    r/singularity, r/ChatGPT (via RSS)
"""

import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.weak_signals")

# ── arXiv ─────────────────────────────────────────────────────────────────────
ARXIV_QUERIES = [
    "cat:cs.AI AND (LLM OR language model OR agent OR alignment OR reasoning)",
    "cat:cs.LG AND (transformer OR fine-tuning OR RLHF OR foundation model OR benchmark)",
    "cat:cs.CL AND (instruction following OR RAG OR reasoning OR multimodal OR safety)",
    "cat:cs.CV AND (multimodal OR vision language OR diffusion OR image generation OR video)",
]

# ── Repos GitHub surveillés en permanence ─────────────────────────────────────
WATCHED_REPOS = [
    {"repo": "dair-ai/ML-Papers-of-the-Week",  "name": "ML Papers of the Week"},
    {"repo": "deepseek-ai/DeepSeek-V3",         "name": "DeepSeek-V3"},
    {"repo": "ollama/ollama",                   "name": "Ollama"},
]

# ── GitHub search queries (signaux faibles < 500 stars) ──────────────────────
GITHUB_SEARCH_QUERIES = [
    "AI LLM agent",
    "large language model",
    "RAG retrieval augmented generation",
    "fine-tuning llama mistral",
]

# ── Reddit RSS ────────────────────────────────────────────────────────────────
REDDIT_FEEDS = [
    {"name": "r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/hot/.rss"},
    {"name": "r/LocalLLaMA",      "url": "https://www.reddit.com/r/LocalLLaMA/new/.rss"},
    {"name": "r/artificial",      "url": "https://www.reddit.com/r/artificial/hot/.rss"},
    {"name": "r/singularity",     "url": "https://www.reddit.com/r/singularity/hot/.rss"},
    {"name": "r/ChatGPT",         "url": "https://www.reddit.com/r/ChatGPT/hot/.rss"},
]


def _hours_ago(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


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


# ── arXiv (API Atom) ──────────────────────────────────────────────────────────

async def fetch_arxiv(hours: int = 48) -> list[dict]:
    """Collecte les papiers arXiv via l'API Atom."""
    signals = []

    async with httpx.AsyncClient(timeout=20) as client:
        for query in ARXIV_QUERIES:
            try:
                resp = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={
                        "search_query": query,
                        "sortBy":       "submittedDate",
                        "sortOrder":    "descending",
                        "max_results":  12,
                    },
                )
                if resp.status_code != 200:
                    continue

                feed  = feedparser.parse(resp.text)
                count = 0
                for entry in feed.entries:
                    title    = entry.get("title", "").strip().replace("\n", " ")
                    url      = entry.get("id", entry.get("link", "")).strip()
                    abstract = entry.get("summary", "").strip()[:500]

                    if not title or not url or not _is_within(entry, hours):
                        continue

                    signals.append({
                        "sector":      "ai",
                        "category":    "weak_signal",
                        "source_name": "arXiv Research",
                        "source_url":  url,
                        "title":       f"[Paper] {title}",
                        "raw_content": abstract,
                        "stars_count": 0,
                    })
                    count += 1

                if count:
                    logger.info(f"arXiv '{query[:45]}...': {count} papiers")

            except Exception as e:
                logger.warning(f"arXiv erreur: {e}")

    # Dédupliquer
    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    logger.info(f"arXiv TOTAL: {len(unique)} papiers")
    return unique


# ── Repos GitHub spécifiques (releases + commits récents) ────────────────────

async def fetch_watched_repos(hours: int = 48) -> list[dict]:
    """
    Surveille les repos GitHub clés pour leurs releases et derniers commits.
    """
    signals = []
    cutoff  = _hours_ago(hours)

    async with httpx.AsyncClient(
        timeout=15,
        headers={"Accept": "application/vnd.github.v3+json"},
    ) as client:
        for repo_info in WATCHED_REPOS:
            repo = repo_info["repo"]
            name = repo_info["name"]

            # 1. Releases récentes
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{repo}/releases",
                    params={"per_page": 5},
                )
                if resp.status_code == 200:
                    for release in resp.json():
                        published = release.get("published_at", "")
                        if not published:
                            continue
                        try:
                            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                            if dt < cutoff:
                                continue
                        except Exception:
                            pass

                        tag   = release.get("tag_name", "")
                        body  = (release.get("body") or "")[:400]
                        url   = release.get("html_url", f"https://github.com/{repo}/releases")

                        signals.append({
                            "sector":      "ai",
                            "category":    "weak_signal",
                            "source_name": name,
                            "source_url":  url,
                            "title":       f"[Release] {name} {tag}",
                            "raw_content": body or f"Nouvelle release {tag} pour {repo}",
                            "stars_count": 0,
                        })
                        logger.info(f"GitHub watched — {repo}: release {tag}")

            except Exception as e:
                logger.debug(f"Releases {repo}: {e}")

            # 2. Derniers commits sur main/master
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{repo}/commits",
                    params={"per_page": 3},
                )
                if resp.status_code == 200:
                    for commit in resp.json():
                        date_str = commit.get("commit", {}).get("author", {}).get("date", "")
                        if not date_str:
                            continue
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if dt < cutoff:
                                continue
                        except Exception:
                            pass

                        msg = commit.get("commit", {}).get("message", "").split("\n")[0][:120]
                        sha = commit.get("sha", "")[:7]
                        url = commit.get("html_url", f"https://github.com/{repo}")

                        # Ne garder que les commits avec un message significatif
                        if len(msg) < 10 or msg.lower().startswith("merge"):
                            continue

                        signals.append({
                            "sector":      "ai",
                            "category":    "weak_signal",
                            "source_name": name,
                            "source_url":  url,
                            "title":       f"[Commit] {name}: {msg}",
                            "raw_content": f"Commit {sha}: {msg}",
                            "stars_count": 0,
                        })

            except Exception as e:
                logger.debug(f"Commits {repo}: {e}")

    logger.info(f"Repos surveillés TOTAL: {len(signals)} signaux")
    return signals


# ── GitHub signaux faibles (repos récents < 500 stars) ───────────────────────

async def fetch_github_weak(hours: int = 96) -> list[dict]:
    """Repos IA récents à forte vélocité (30-500 stars)."""
    signals = []
    cutoff_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient(
        timeout=15,
        headers={"Accept": "application/vnd.github.v3+json"},
    ) as client:
        for query in GITHUB_SEARCH_QUERIES[:3]:
            try:
                search_q = f"{query} stars:30..500 created:>{cutoff_date}"
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": search_q, "sort": "stars", "order": "desc", "per_page": 5},
                )
                if resp.status_code == 200:
                    for repo in resp.json().get("items", []):
                        name        = repo.get("full_name", "")
                        description = repo.get("description", "") or ""
                        url         = repo.get("html_url", "")
                        stars       = repo.get("stargazers_count", 0)

                        signals.append({
                            "sector":      "ai",
                            "category":    "weak_signal",
                            "source_name": "GitHub Émergent",
                            "source_url":  url,
                            "title":       f"[GitHub] {name} — {description[:100]}",
                            "raw_content": f"{description} | Stars: {stars}",
                            "stars_count": stars,
                        })
                elif resp.status_code == 403:
                    logger.warning("GitHub API rate limit — GitHub weak ignoré")
                    break
            except Exception as e:
                logger.warning(f"GitHub weak erreur '{query}': {e}")

    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    logger.info(f"GitHub faibles TOTAL: {len(unique)} repos")
    return unique


# ── Reddit (RSS public) ───────────────────────────────────────────────────────

async def fetch_reddit(hours: int = 48) -> list[dict]:
    """Collecte les posts Reddit via flux RSS public."""
    signals = []

    for feed_info in REDDIT_FEEDS:
        try:
            feed  = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                if not _is_within(entry, hours):
                    continue

                title   = entry.get("title", "").strip()
                url     = entry.get("link", "").strip()
                content = entry.get("summary", entry.get("description", ""))
                content = content[:400] if content else title

                if not title or not url:
                    continue

                signals.append({
                    "sector":      "ai",
                    "category":    "weak_signal",
                    "source_name": feed_info["name"],
                    "source_url":  url,
                    "title":       title,
                    "raw_content": content,
                    "stars_count": 0,
                })
                count += 1

            if count:
                logger.info(f"Reddit {feed_info['name']}: {count} posts")
        except Exception as e:
            logger.warning(f"Reddit erreur {feed_info['name']}: {e}")

    logger.info(f"Reddit TOTAL: {len(signals)} posts")
    return signals


# ── Point d'entrée ────────────────────────────────────────────────────────────

async def collect(hours: int = 48) -> list[dict]:
    """Collecte tous les signaux faibles."""
    import asyncio
    arxiv, watched, github, reddit = await asyncio.gather(
        fetch_arxiv(hours),
        fetch_watched_repos(hours),
        fetch_github_weak(hours),
        fetch_reddit(hours),
        return_exceptions=True,
    )

    def _safe(r, n):
        if isinstance(r, Exception):
            logger.error(f"Collect {n} échoué: {r}")
            return []
        return r

    arxiv   = _safe(arxiv,   "arXiv")
    watched = _safe(watched, "repos surveillés")
    github  = _safe(github,  "GitHub faibles")
    reddit  = _safe(reddit,  "Reddit")

    total = arxiv + watched + github + reddit
    logger.info(
        f"Signaux Faibles TOTAL: {len(total)} "
        f"({len(arxiv)} arXiv, {len(watched)} repos, {len(github)} GitHub, {len(reddit)} Reddit)"
    )
    return total
