"""
CORTEX — Agent SCOUT-DEEPTECH v1
Collecte : signaux deeptech (biotech, quantum, robotique, énergie, matériaux, espace)

Sources :
  - arXiv API : quant-ph, cond-mat, physics.bio-ph, eess.SY, cs.RO
  - bioRxiv RSS (biologie)
  - Nature News RSS
  - MIT Technology Review RSS
  - IEEE Spectrum RSS
  - DARPA News RSS
"""

import asyncio
import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.deeptech")

ARXIV_API_URL = "https://export.arxiv.org/api/query"

# arXiv categories deeptech (hors IA pure couverte par SCOUT-AI)
DEEPTECH_ARXIV_QUERIES = [
    "cat:quant-ph AND (quantum computing OR quantum hardware OR qubit OR error correction)",
    "cat:cond-mat AND (material OR battery OR superconductor OR 2D material OR graphene)",
    "cat:physics.bio-ph AND (protein OR drug discovery OR CRISPR OR gene OR biosensor)",
    "cat:eess.SY AND (energy OR grid OR fusion OR solar OR storage OR nuclear)",
    "cat:cs.RO AND (robot OR manipulation OR locomotion OR humanoid OR autonomous)",
]

DEEPTECH_RSS_FEEDS = [
    {"name": "Nature News",          "url": "https://www.nature.com/news.rss"},
    {"name": "MIT Tech Review",      "url": "https://www.technologyreview.com/feed/"},
    {"name": "IEEE Spectrum",        "url": "https://spectrum.ieee.org/rss/fulltext"},
    {"name": "bioRxiv",              "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience"},
    {"name": "DARPA News",           "url": "https://www.darpa.mil/rss-feeds/news"},
    {"name": "Ars Technica Science", "url": "https://feeds.arstechnica.com/arstechnica/science"},
]

DEEPTECH_KEYWORDS = [
    "quantum", "qubit", "superconductor", "fusion", "plasma",
    "biotech", "crispr", "gene", "protein", "drug discovery",
    "robot", "humanoid", "exoskeleton", "autonomous",
    "battery", "energy storage", "solar", "wind", "nuclear",
    "nanotechnology", "graphene", "material", "2d material",
    "space", "satellite", "launch", "rocket", "starship",
    "neuro", "brain", "bci", "implant", "neuralink",
    "breakthrough", "first-ever", "milestone", "record",
]

DEEPTECH_NOISE = [
    "chatgpt", "chatbot", "llm", "language model", "gpt", "claude",
    "openai", "anthropic", "gemini", "llama", "fine-tun",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_deeptech(text: str) -> bool:
    t = text.lower()
    if any(kw in t for kw in DEEPTECH_NOISE):
        return False
    return any(kw in t for kw in DEEPTECH_KEYWORDS)


# ── arXiv deeptech ────────────────────────────────────────────────────────────

async def _fetch_arxiv_deeptech(client: httpx.AsyncClient, query: str) -> list[dict]:
    try:
        r = await client.get(
            ARXIV_API_URL,
            params={
                "search_query": query,
                "max_results":  10,
                "sortBy":       "submittedDate",
                "sortOrder":    "descending",
            },
            timeout=15,
        )
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        signals = []
        for entry in root.findall("atom:entry", ns):
            title   = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip()[:500]
            url     = entry.findtext("atom:id", "", ns).strip()
            # Author
            authors = entry.findall("atom:author", ns)
            author  = authors[0].findtext("atom:name", "", ns) if authors else ""

            # Published date
            pub = entry.findtext("atom:published", "", ns)

            if not title or not url:
                continue

            # Detect domain
            domain = "Recherche"
            q_lower = query.lower()
            if "quant-ph" in q_lower:     domain = "Quantique"
            elif "cond-mat" in q_lower:   domain = "Matériaux"
            elif "bio-ph" in q_lower:     domain = "Biotech"
            elif "eess.sy" in q_lower:    domain = "Énergie"
            elif "cs.ro" in q_lower:      domain = "Robotique"

            signals.append({
                "title":       title,
                "source_name": f"arXiv — {domain}",
                "source_url":  url,
                "raw_content": f"Auteur: {author}. {summary}",
                "sector":      "deeptech",
                "category":    "research",
                "domain":      domain,
                "published":   pub,
            })
        return signals
    except Exception as e:
        logger.warning(f"arXiv deeptech '{query[:30]}': {e}")
        return []


# ── RSS feeds deeptech ────────────────────────────────────────────────────────

async def _fetch_rss_feed(feed_info: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = []
    try:
        feed = await asyncio.to_thread(feedparser.parse, feed_info["url"])
        for entry in feed.entries[:15]:
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
            content = entry.get("summary", entry.get("description", ""))[:500]

            if not title or not url:
                continue
            if not _is_deeptech(title + " " + content):
                continue

            signals.append({
                "title":       title,
                "source_name": feed_info["name"],
                "source_url":  url,
                "raw_content": content,
                "sector":      "deeptech",
                "category":    "media",
            })
    except Exception as e:
        logger.warning(f"DeepTech RSS {feed_info['name']}: {e}")
    return signals


# ── Point d'entrée principal ──────────────────────────────────────────────────

async def collect(hours: int = 48) -> list[dict]:
    """
    Lance la collecte complète SCOUT-DEEPTECH.
    Retourne une liste de signaux deeptech bruts.
    """
    headers = {"User-Agent": "CORTEX/1.0"}
    async with httpx.AsyncClient(headers=headers) as client:
        arxiv_tasks = [_fetch_arxiv_deeptech(client, q) for q in DEEPTECH_ARXIV_QUERIES]
        arxiv_results = await asyncio.gather(*arxiv_tasks, return_exceptions=True)

    rss_results = await asyncio.gather(
        *[_fetch_rss_feed(f, hours) for f in DEEPTECH_RSS_FEEDS],
        return_exceptions=True,
    )

    all_signals = []
    for r in arxiv_results:
        if isinstance(r, list):
            all_signals.extend(r)
    for r in rss_results:
        if isinstance(r, list):
            all_signals.extend(r)

    # Déduplication
    seen, unique = set(), []
    for s in all_signals:
        url = s.get("source_url", "")
        title = s.get("title", "").lower()[:60]
        key = url or title
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    logger.info(f"SCOUT-DEEPTECH: {len(unique)} signaux ({hours}h)")
    return unique
