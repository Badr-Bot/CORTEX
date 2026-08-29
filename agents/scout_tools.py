"""
CORTEX — Agent SCOUT-TOOLS : la boîte à outils e-commerce.

Ce que Badr veut voir chaque matin, en plus des news : les OUTILS concrets qu'il
peut utiliser cette semaine pour sa boutique — générer des vidéos, trouver un
produit gagnant, analyser un marché, scraper des concurrents, automatiser ses
pubs Meta, répondre au service client, écrire des fiches produit.

Sources (toutes gratuites, sans clé) :
  - GitHub : repos récents qui montent sur ces usages + skills/plugins Claude
  - Hugging Face : modèles vidéo/image en tendance (créas publicitaires)
  - Product Hunt : lancements du jour côté e-commerce / marketing / IA

Chaque outil est classé par usage (voir USAGE_KEYWORDS) pour que l'agent
rédacteur puisse remplir la section "outils" du rapport sans deviner.
"""

import asyncio
from datetime import datetime, timezone, timedelta

import httpx

from utils.github_api import github_headers
from utils.logger import get_logger

logger = get_logger("scout_tools")

# Usages suivis. La clé est celle attendue par le dashboard (EcomToolbox.tsx).
USAGE_KEYWORDS: dict[str, list[str]] = {
    "video": [
        "video", "vidéo", "text-to-video", "image-to-video", "talking head",
        "ugc video", "avatar", "reels", "tiktok video", "short-form", "lipsync",
    ],
    "produit_gagnant": [
        "winning product", "product research", "dropship", "trending product",
        "product finder", "spy", "best seller", "bestseller", "niche finder",
        "aliexpress", "product hunt tool",
    ],
    "analyse_marche": [
        "market analysis", "market research", "competitor", "competitive",
        "trend analysis", "keyword research", "seo audit", "demand", "benchmark",
        "insights", "analytics", "analyse de marché",
    ],
    "scraping": [
        "scraper", "scraping", "crawler", "crawl", "extract data", "parse",
        "playwright", "puppeteer", "selenium", "browser automation", "web data",
    ],
    "pub": [
        "meta ads", "facebook ads", "tiktok ads", "google ads", "ad creative",
        "ad copy", "campaign", "roas", "advertis", "ads manager", "creative testing",
        "ugc ads", "advantage+",
    ],
    "fiches_produit": [
        "product description", "product page", "product listing", "listing",
        "product photo", "product image", "background removal", "mockup",
        "copywriting", "fiche produit",
    ],
    "service_client": [
        "customer support", "customer service", "support agent", "helpdesk",
        "chatbot", "live chat", "faq", "ticket", "inbox", "service client",
    ],
    "skill_claude": [
        "claude skill", "claude code", "skill.md", "claude plugin", "mcp server",
        "model context protocol", "agent skill", "claude agent",
    ],
    "automatisation": [
        "automation", "automate", "workflow", "n8n", "zapier", "make.com",
        "agent", "autonomous", "pipeline", "shopify app", "shopify api",
        "klaviyo", "email flow", "erp", "inventory", "fulfillment",
    ],
}

USAGES = list(USAGE_KEYWORDS.keys())

# Bruit : pas des outils utilisables par un e-commerçant
TOOL_NOISE = [
    "awesome list", "curated list", "interview questions", "leetcode",
    "homework", "course materials", "tutorial series", "my portfolio",
    "cheat sheet", "roadmap", "wallpaper",
]

# Requêtes GitHub : repos CRÉÉS récemment (nouveautés), pas les géants établis.
# Une par usage, volontairement larges : le classement affine ensuite.
GITHUB_QUERIES = [
    ("shopify OR woocommerce OR \"e-commerce\" OR ecommerce", 15),
    ("\"meta ads\" OR \"facebook ads\" OR \"tiktok ads\" OR \"ad creative\"", 10),
    ("\"product research\" OR \"winning products\" OR dropshipping", 10),
    ("scraper (amazon OR tiktok OR shopify OR instagram OR ecommerce)", 30),
    ("\"text-to-video\" OR \"video generation\" OR \"talking head\" OR ugc", 100),
    ("\"claude code\" OR \"claude skills\" OR \"skill.md\" OR \"mcp server\"", 40),
    ("\"customer support\" agent OR \"shopping agent\" OR \"ai agent\" ecommerce", 30),
    ("\"product description\" generator OR \"product photo\" OR \"background removal\"", 20),
]

GITHUB_CREATED_DAYS = 45

# Product Hunt : flux public, on ne garde que ce qui parle à une boutique en ligne
PRODUCT_HUNT_FEED = {"name": "Product Hunt", "url": "https://www.producthunt.com/feed"}
PRODUCT_HUNT_KEYWORDS = [
    "ecommerce", "e-commerce", "shopify", "store", "seller", "dropship", "ads",
    "advertising", "marketing", "video", "ugc", "creative", "email", "sms",
    "customer", "support", "chatbot", "ai agent", "automation", "scrap",
    "product", "tiktok", "instagram", "influencer", "seo", "conversion",
]

# Uniquement les modèles qui PRODUISENT des images ou des vidéos (créas).
# "image-text-to-text" = des chatbots qui lisent des images : pas des outils de créa.
HF_VISUAL_PIPELINES = {
    "text-to-video", "image-to-video", "video-to-video",
    "text-to-image", "image-to-image",
}
# Copies quantifiées / dérivées d'un même modèle : on garde l'original.
HF_VARIANT_MARKERS = ("gguf", "fp8", "fp4", "int4", "int8", "awq", "gptq", "mlx",
                      "abliterated", "uncensored", "exl2", "nf4")
HF_MAX_MODELS = 8


def classify_usage(text: str, default: str = "automatisation") -> str:
    """Attribue un usage à un outil selon le vocabulaire présent.

    Le premier usage qui atteint le meilleur score gagne ; à score nul on
    retombe sur `default`. "skill_claude" et "video" priment à égalité parce
    que ce sont les deux demandes explicites de Badr.
    """
    t = text.lower()
    scores = {u: sum(1 for kw in kws if kw in t) for u, kws in USAGE_KEYWORDS.items()}
    best_score = max(scores.values())
    if best_score == 0:
        return default
    for priority in ("skill_claude", "video"):
        if scores[priority] == best_score:
            return priority
    return max(scores, key=scores.get)


def is_tool_relevant(text: str) -> bool:
    t = text.lower()
    if any(noise in t for noise in TOOL_NOISE):
        return False
    return any(kw in t for kws in USAGE_KEYWORDS.values() for kw in kws)


def is_hf_variant(model_id: str) -> bool:
    """Copie quantifiée ou dérivée (GGUF, FP8, uncensored…) d'un modèle existant."""
    low = model_id.lower()
    return any(marker in low for marker in HF_VARIANT_MARKERS)


def _tool(name: str, url: str, source: str, summary: str, usage: str,
          popularity: int = 0, free: bool = True) -> dict:
    return {
        "sector":      "tools",
        "category":    "tool",
        "source_name": source,
        "source_url":  url,
        "title":       name,
        "raw_content": summary,
        "usage":       usage,
        "stars_count": popularity,
        "gratuit":     free,
    }


# ── GitHub ───────────────────────────────────────────────────────────────────

async def fetch_github_tools(days: int = GITHUB_CREATED_DAYS) -> list[dict]:
    """Repos créés récemment autour des usages e-commerce, triés par étoiles."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    tools: list[dict] = []

    async with httpx.AsyncClient(timeout=15, headers=github_headers()) as client:
        for query, min_stars in GITHUB_QUERIES:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} created:>{cutoff} stars:>={min_stars}",
                        "sort": "stars", "order": "desc", "per_page": 8,
                    },
                )
                if resp.status_code == 403:
                    logger.warning("GitHub API rate limit — outils GitHub tronqués")
                    break
                if resp.status_code != 200:
                    continue
                for repo in resp.json().get("items", []):
                    name = repo.get("full_name", "")
                    desc = (repo.get("description") or "").strip()
                    text = f"{name} {desc} {' '.join(repo.get('topics') or [])}"
                    if not desc or not is_tool_relevant(text):
                        continue
                    stars = repo.get("stargazers_count", 0)
                    tools.append(_tool(
                        name=name,
                        url=repo.get("html_url", ""),
                        source=f"GitHub ({repo.get('language') or 'code'})",
                        summary=f"Stars: {stars:,} | {desc}",
                        usage=classify_usage(text),
                        popularity=stars,
                    ))
            except Exception as e:
                logger.warning(f"GitHub outils erreur '{query[:30]}': {e}")
            # L'API de recherche est limitée à la minute : on espace les appels.
            await asyncio.sleep(1.5)

    logger.info(f"Outils GitHub: {len(tools)} repos")
    return tools


# ── Hugging Face — modèles image/vidéo ──────────────────────────────────────

async def fetch_hf_visual_models(limit: int = 40) -> list[dict]:
    """Modèles image/vidéo en tendance : la matière première des créas pub."""
    tools: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://huggingface.co/api/models",
                params={"sort": "trendingScore", "direction": "-1", "limit": limit},
            )
        if resp.status_code != 200:
            return []
        for item in resp.json():
            pipeline = item.get("pipeline_tag", "")
            if pipeline not in HF_VISUAL_PIPELINES:
                continue
            model_id = item.get("id") or item.get("modelId") or ""
            if not model_id or is_hf_variant(model_id):
                continue
            if len(tools) >= HF_MAX_MODELS:
                break
            likes = item.get("likes", 0)
            usage = "video" if "video" in pipeline else "fiches_produit"
            tools.append(_tool(
                name=model_id,
                url=f"https://huggingface.co/{model_id}",
                source=f"Hugging Face ({pipeline})",
                summary=(f"Modèle {pipeline} | Likes: {likes:,} | "
                         f"Téléchargements: {item.get('downloads', 0):,}"),
                usage=usage,
                popularity=likes,
            ))
    except Exception as e:
        logger.warning(f"Hugging Face visuel erreur: {e}")

    logger.info(f"Outils Hugging Face: {len(tools)} modèles image/vidéo")
    return tools


# ── Product Hunt ─────────────────────────────────────────────────────────────

async def fetch_product_hunt(hours: int = 72) -> list[dict]:
    """Lancements Product Hunt utiles à une boutique en ligne (souvent payants)."""
    from utils.feeds import collect_feed_entries

    def _relevant(text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in PRODUCT_HUNT_KEYWORDS) and not any(n in t for n in TOOL_NOISE)

    entries = await collect_feed_entries(
        PRODUCT_HUNT_FEED, hours=hours, sector="tools",
        is_relevant=_relevant, max_entries=60,
    )
    tools = [
        _tool(
            name=e["title"], url=e["source_url"], source="Product Hunt",
            summary=e["raw_content"],
            usage=classify_usage(f"{e['title']} {e['raw_content']}"),
            free=False,
        )
        for e in entries
    ]
    logger.info(f"Outils Product Hunt: {len(tools)} lancements")
    return tools


# ── Point d'entrée ───────────────────────────────────────────────────────────

def dedupe_and_sort(tools: list[dict]) -> list[dict]:
    """Dédoublonne par URL, puis alterne les usages (les plus populaires d'abord
    dans chaque usage) : sans ça, une seule famille de modèles occupe tout le
    haut de la liste et l'agent ne voit jamais les outils de scraping ou de pub."""
    seen, unique = set(), []
    for t in tools:
        if t["source_url"] and t["source_url"] not in seen:
            seen.add(t["source_url"])
            unique.append(t)
    unique.sort(key=lambda t: t.get("stars_count", 0), reverse=True)

    par_usage: dict[str, list[dict]] = {}
    for t in unique:
        par_usage.setdefault(t["usage"], []).append(t)
    files = [par_usage[u] for u in USAGES if u in par_usage]
    ordered: list[dict] = []
    while files:
        for f in files:
            ordered.append(f.pop(0))
        files = [f for f in files if f]
    return ordered


async def collect(hours: int = 72) -> dict:
    """Retourne {tools: list[dict], usages: {usage: nombre}}."""
    github, hf, ph = await asyncio.gather(
        fetch_github_tools(), fetch_hf_visual_models(), fetch_product_hunt(hours),
        return_exceptions=True,
    )
    tools: list[dict] = []
    for name, result in (("GitHub", github), ("Hugging Face", hf), ("Product Hunt", ph)):
        if isinstance(result, Exception):
            logger.error(f"Outils {name} échoué: {result}")
        else:
            tools.extend(result)

    tools = dedupe_and_sort(tools)
    usages: dict[str, int] = {}
    for t in tools:
        usages[t["usage"]] = usages.get(t["usage"], 0) + 1
    logger.info(f"SCOUT-TOOLS: {len(tools)} outils — {usages}")
    return {"tools": tools, "usages": usages}
