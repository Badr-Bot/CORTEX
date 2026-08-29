"""
CORTEX — Enquête sur un candidat du radar : le vrai produit + les vraies douleurs.

Leçon MASTER ACQUISITION · 08 « Analyse marketing » : avant d'écrire une pub,
scraper les avis et les forums pour trouver les vrais angles, les objections,
les douleurs que les gens vivent — pas celles qu'on imagine.

Pour chaque boutique demandée :
  1. la fiche produit réelle (`/products.json` de Shopify) — parce que le titre
     TrendTrack ne dit pas ce que c'est (un « Fascial Release » était un complément)
  2. Reddit (recherche publique JSON) sur les mots-clés FR et EN : les posts et
     commentaires où les gens racontent le problème, classés par intensité
     (lexique de douleur forte : « je n'en peux plus », « cauchemar », « can't
     sleep »…)

Tourne là où il y a du réseau (GitHub Actions `radar_enquete.yml`, ou en
local). Le bac à sable de la routine n'a pas de réseau : la routine écrit une
demande, pousse, et récupère le résultat.

Usage :
    python -m agents.radar_enquete AAAA-MM-JJ            # lit data/radar/enquete_request_AAAA-MM-JJ.json
Demande :
    [{"boutique": "pestprohome.com", "produit": "…",
      "mots_cles_fr": ["cafards appartement", "souris dans les murs"],
      "mots_cles_en": ["cockroaches apartment", "mice in walls"]}]
Sorties : data/radar/enquete_AAAA-MM-JJ.json et .md
"""

import asyncio
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from utils.logger import get_logger

logger = get_logger("radar_enquete")

RADAR_DIR = Path(__file__).parent.parent / "data" / "radar"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36 cortex-radar/1.0"

# Ce qui distingue une douleur FORTE (on paie pour que ça s'arrête) d'une gêne.
DOULEUR_FORTE = [
    "je n'en peux plus", "j'en peux plus", "cauchemar", "phobie", "je ne dors plus", "insomnie",
    "honte", "dégoût", "degout", "désespoir", "desespoir", "pleur", "angoisse", "panique",
    "tout essayé", "rien ne marche", "depuis des mois", "depuis des années", "infest",
    "nightmare", "can't sleep", "cant sleep", "anxiety", "disgusting", "desperate", "tried everything",
    "nothing works", "for months", "for years", "embarrass", "ashamed", "crying", "panic", "phobia",
    "landlord", "propriétaire", "won't do anything", "ne fait rien",
]
DOULEUR_MOYENNE = [
    "énervant", "agaçant", "chiant", "galère", "pénible", "annoying", "frustrating", "gross", "ugh",
]

SUBREDDITS_HINT = ""  # recherche globale : les sous-forums FR sont trop petits

MAX_POSTS_PAR_MOT = 25
MIN_SCORE = 3


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(s or "")).replace("\xa0", " ").strip()


def intensite(texte: str) -> tuple[str, list[str]]:
    t = texte.lower()
    fortes = [m for m in DOULEUR_FORTE if m in t]
    if fortes:
        return "forte", fortes
    moyennes = [m for m in DOULEUR_MOYENNE if m in t]
    return ("moyenne", moyennes) if moyennes else ("faible", [])


# ── Fiche produit réelle ──────────────────────────────────────────────────────

async def fiche_produit(client: httpx.AsyncClient, boutique: str) -> dict:
    url = f"https://{boutique}/products.json?limit=10"
    try:
        r = await client.get(url, timeout=15)
        if r.status_code != 200:
            return {"erreur": f"HTTP {r.status_code}"}
        produits = []
        for p in r.json().get("products", [])[:10]:
            variants = p.get("variants") or []
            prix = sorted({float(v.get("price") or 0) for v in variants if v.get("price")})
            produits.append({
                "titre": p.get("title"),
                "type": p.get("product_type") or "",
                "tags": p.get("tags") or [],
                "prix": prix,
                "description": _strip_html(p.get("body_html") or "")[:1200],
            })
        return {"produits": produits}
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {str(e)[:120]}"}


# ── Reddit ────────────────────────────────────────────────────────────────────

async def reddit_search(client: httpx.AsyncClient, mot: str, limit: int = MAX_POSTS_PAR_MOT) -> list[dict]:
    """Posts Reddit pour un mot-clé. L'API JSON renvoie 403 sans jeton depuis
    2026 ; le flux RSS de la recherche, lui, reste ouvert (pas de score, on
    classe par intensité puis par date)."""
    import feedparser

    out = []
    try:
        r = None
        for tentative in range(3):
            r = await client.get(
                "https://www.reddit.com/search.rss",
                params={"q": mot, "sort": "relevance", "t": "year", "limit": limit},
                timeout=20,
            )
            if r.status_code != 429:
                break
            await asyncio.sleep(5 * (tentative + 1))  # Reddit limite à ~1 requête toutes les 2 s
        if r is None or r.status_code != 200:
            logger.warning(f"Reddit '{mot}' → HTTP {r.status_code if r else '?'}")
            return []
        feed = feedparser.parse(r.content)
        for e in feed.entries:
            titre = (e.get("title") or "").strip()
            contenu = _strip_html((e.get("summary") or "") if not e.get("content") else e["content"][0].get("value", ""))
            # Le flux ajoute une ligne « submitted by /u/x [link] [comments] » : on la retire.
            contenu = re.sub(r"submitted by\s+/u/\S+.*$", "", contenu, flags=re.S).strip()
            link = e.get("link") or ""
            m = re.search(r"reddit\.com/r/([^/]+)/", link)
            niveau, marqueurs = intensite(f"{titre}\n{contenu}")
            date = ""
            if e.get("updated_parsed"):
                date = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
            out.append({
                "mot_cle": mot,
                "titre": titre,
                "extrait": contenu[:600],
                "subreddit": m.group(1) if m else "",
                "score": 0,
                "commentaires": 0,
                "url": link,
                "date": date,
                "intensite": niveau,
                "marqueurs": marqueurs,
            })
    except Exception as e:
        logger.warning(f"Reddit '{mot}' erreur: {e}")
    return out


def trier_douleurs(posts: list[dict]) -> list[dict]:
    """Doublons retirés, douleurs fortes d'abord, puis par score."""
    seen, unique = set(), []
    for p in posts:
        if p["url"] in seen or (0 < p["score"] < MIN_SCORE and p["intensite"] != "forte"):
            continue
        seen.add(p["url"])
        unique.append(p)
    rang = {"forte": 0, "moyenne": 1, "faible": 2}
    unique.sort(key=lambda p: (rang[p["intensite"]], -(p["score"] + 2 * p["commentaires"]), p.get("date", "")), )
    unique.sort(key=lambda p: rang[p["intensite"]])
    return unique


# ── Orchestration ─────────────────────────────────────────────────────────────

async def enqueter(demandes: list[dict]) -> list[dict]:
    resultats = []
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as client:
        for d in demandes:
            boutique = d.get("boutique", "").replace("https://", "").strip("/")
            mots = list(d.get("mots_cles_fr", [])) + list(d.get("mots_cles_en", []))
            fiche = await fiche_produit(client, boutique)
            posts = []
            for mot in mots[:8]:
                posts += await reddit_search(client, mot)
                await asyncio.sleep(2.5)  # Reddit tolère ~1 requête toutes les 2 s sans jeton
            douleurs = trier_douleurs(posts)
            resultats.append({
                "boutique": boutique,
                "produit": d.get("produit", ""),
                "fiche": fiche,
                "douleurs": douleurs[:30],
                "compte": {"posts": len(posts), "fortes": sum(1 for p in douleurs if p["intensite"] == "forte")},
            })
            logger.info(f"Enquête {boutique} : {len(posts)} posts, {resultats[-1]['compte']['fortes']} douleurs fortes")
    return resultats


def format_md(resultats: list[dict], date: str) -> str:
    lines = [f"# Enquête radar — {date}", "",
             "Pour chaque candidat : la vraie fiche produit, puis les douleurs réelles trouvées sur Reddit,",
             "les plus fortes d'abord (citations et liens : à recopier, jamais à inventer).", ""]
    for r in resultats:
        lines += [f"## {r['produit']} — {r['boutique']}", ""]
        fiche = r["fiche"]
        if fiche.get("erreur"):
            lines.append(f"Fiche produit : indisponible ({fiche['erreur']})")
        for p in fiche.get("produits", [])[:5]:
            prix = ", ".join(f"{x:g}" for x in p["prix"][:4])
            lines.append(f"- **{p['titre']}** ({prix}) {('· ' + p['type']) if p['type'] else ''}")
            if p["description"]:
                lines.append(f"  {p['description'][:400]}")
        lines += ["", f"### Douleurs trouvées ({r['compte']['fortes']} fortes sur {r['compte']['posts']} posts)", ""]
        for p in r["douleurs"][:15]:
            tag = "🔴 FORTE" if p["intensite"] == "forte" else ("🟠 moyenne" if p["intensite"] == "moyenne" else "⚪ faible")
            lines.append(f"- {tag} [{p['mot_cle']}] r/{p['subreddit']} · {p['score']} pts · {p['commentaires']} com. · {p['date']}")
            lines.append(f"  **{p['titre']}**")
            if p["extrait"]:
                lines.append(f"  « {p['extrait'][:350].replace(chr(10), ' ')} »")
            if p["marqueurs"]:
                lines.append(f"  marqueurs : {', '.join(p['marqueurs'][:4])}")
            lines.append(f"  {p['url']}")
        lines.append("")
    return "\n".join(lines)


async def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    date = args[0] if args else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    req = RADAR_DIR / f"enquete_request_{date}.json"
    if not req.exists():
        logger.error(f"Demande introuvable : {req}")
        return 1
    demandes = json.loads(req.read_text(encoding="utf-8"))
    resultats = await enqueter(demandes)
    (RADAR_DIR / f"enquete_{date}.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")
    (RADAR_DIR / f"enquete_{date}.md").write_text(format_md(resultats, date), encoding="utf-8")
    logger.info(f"Enquête écrite : {len(resultats)} boutiques")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
