"""
CORTEX — Agent SCOUT-ECOMMERCE v1
Collecte : nouveautés e-commerce, réparties en 5 thèmes.

Thèmes suivis (demandés par Badr) :
  - marketplace : Shopify, Amazon, TikTok Shop, Temu, marketplaces, D2C
  - automation  : automatisation, agents IA, agentic commerce, no-code, ERP/OMS
  - emailing    : email marketing, Klaviyo, SMS, rétention, délivrabilité, CRM
  - creatives   : publicités, créas, UGC, Meta/TikTok Ads, contenu qui convertit
  - operations  : logistique, paiement, supply chain, fraude, retours

Sources : RSS métier (Modern Retail, Retail Dive, Practical Ecommerce...) +
requêtes Google News ciblées par thème (couverture des sujets chauds du jour).

Dashboard : actions cotées du secteur e-commerce via Yahoo Finance.
"""

import asyncio
import httpx

from utils.logger import get_logger

logger = get_logger("scout_ai.ecommerce")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Actions cotées représentatives de l'e-commerce (plateformes, marketplaces, outils)
ECOM_TICKERS = {
    "Shopify":       "SHOP",
    "Amazon":        "AMZN",
    "MercadoLibre":  "MELI",
    "Sea Limited":   "SE",
    "Etsy":          "ETSY",
    "Global-e":      "GLBE",
    "Wayfair":       "W",
    "Chewy":         "CHWY",
    "Klaviyo":       "KVYO",
    "PayPal":        "PYPL",
}

# ── Flux ─────────────────────────────────────────────────────────────────────
# Vérifiés le 2026-08-12. Écartés car 403/404/vides : Retail TouchPoints,
# RetailWire, Marketplace Pulse, Search Engine Land, blogs Klaviyo/Litmus.
ECOM_NEWS_FEEDS = [
    # Cœur e-commerce / retail
    {"name": "Modern Retail",        "url": "https://www.modernretail.co/feed/",              "theme": "marketplace"},
    {"name": "Retail Dive",          "url": "https://www.retaildive.com/feeds/news/",         "theme": "marketplace"},
    {"name": "Digital Commerce 360", "url": "https://www.digitalcommerce360.com/feed/",       "theme": "marketplace"},
    {"name": "Practical Ecommerce",  "url": "https://www.practicalecommerce.com/feed",        "theme": "automation"},
    {"name": "eCommerceBytes",       "url": "https://www.ecommercebytes.com/feed/",           "theme": "marketplace"},
    {"name": "Ecommerce Times",      "url": "https://www.ecommercetimes.com/rss-feed",        "theme": "automation"},
    {"name": "Supply Chain Dive",    "url": "https://www.supplychaindive.com/feeds/news/",    "theme": "operations"},
    # Marketing / créas / emailing
    {"name": "Marketing Dive",       "url": "https://www.marketingdive.com/feeds/news/",      "theme": "creatives"},
    {"name": "Social Media Today",   "url": "https://www.socialmediatoday.com/feeds/news/",   "theme": "creatives"},
    {"name": "Adweek",               "url": "https://www.adweek.com/feed/",                   "theme": "creatives"},
    {"name": "Search Engine Journal","url": "https://www.searchenginejournal.com/feed/",      "theme": "creatives"},
    # Google News ciblé — capte les sujets chauds que les blogs métier ratent
    {"name": "Plateformes (Google News)",   "theme": "marketplace",
     "url": "https://news.google.com/rss/search?q=Shopify+OR+%22TikTok+Shop%22+OR+%22Amazon+seller%22+OR+Temu+OR+Shein+when:2d&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Emailing (Google News)",      "theme": "emailing",
     "url": "https://news.google.com/rss/search?q=%22email+marketing%22+OR+Klaviyo+OR+%22marketing+automation%22+OR+%22SMS+marketing%22+when:3d&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Automatisation (Google News)", "theme": "automation",
     "url": "https://news.google.com/rss/search?q=%22ecommerce+automation%22+OR+%22agentic+commerce%22+OR+%22AI+shopping+agent%22+OR+%22checkout+AI%22+when:3d&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Créas &amp; pub (Google News)",   "theme": "creatives",
     "url": "https://news.google.com/rss/search?q=%22Meta+ads%22+OR+%22ad+creative%22+OR+%22UGC+ads%22+OR+%22TikTok+ads%22+OR+%22creative+testing%22+when:3d&hl=en-US&gl=US&ceid=US:en"},
]

# ── Classement thématique ────────────────────────────────────────────────────

THEME_KEYWORDS = {
    "emailing": [
        "email marketing", "e-mail", "newsletter", "klaviyo", "mailchimp",
        "sms marketing", "deliverability", "délivrabilité", "open rate",
        "crm", "retention", "rétention", "lifecycle", "segmentation",
        "abandoned cart", "panier abandonné", "loyalty", "fidélité",
    ],
    "automation": [
        "automation", "automat", "ai agent", "agentic", "workflow", "no-code",
        "nocode", "zapier", "n8n", "chatbot", "copilot", "erp", "oms", "pim",
        "inventory management", "auto-fulfillment", "ai shopping", "agent ia",
        "checkout ai", "personalization engine", "dynamic pricing",
    ],
    "creatives": [
        "ad creative", "creative", "créa", "ugc", "influencer", "meta ads",
        "tiktok ads", "google ads", "advertis", "campaign", "brand", "video ad",
        "roas", "cpm", "ctr", "landing page", "conversion rate", "a/b test",
        "seo", "content marketing", "social commerce",
    ],
    "operations": [
        "logistic", "supply chain", "fulfillment", "warehouse", "shipping",
        "delivery", "3pl", "returns", "retour", "payment", "paiement",
        "checkout", "fraud", "tariff", "customs", "douane", "stock",
    ],
    "marketplace": [
        "marketplace", "shopify", "amazon", "tiktok shop", "temu", "shein",
        "etsy", "walmart", "ebay", "alibaba", "d2c", "dtc", "storefront",
        "seller", "vendeur", "dropship", "retail media", "omnichannel",
    ],
}

ECOM_KEYWORDS = [kw for kws in THEME_KEYWORDS.values() for kw in kws] + [
    "ecommerce", "e-commerce", "online store", "boutique en ligne",
    "online retail", "commerce", "shopper", "consumer spending",
]

# Bruit : contenus promotionnels/pédagogiques sans valeur de veille
ECOM_NOISE = [
    "master course", "masterclass", "free course", "tutorial", "webinar",
    "step-by-step guide", "beginner to pro", "how to make money",
    "best deals", "coupon code", "discount code", "black friday deals on",
    "top 10 tools", "sponsored", "press release distribution",
]


def _classify_theme(text: str, default: str = "marketplace", min_score: int = 2) -> str:
    """
    Attribue un thème au signal selon le vocabulaire présent dans le texte.

    Il faut au moins `min_score` mots-clés du thème pour écraser le thème du flux :
    un seul mot déclencheur ("loyalty", "brand"...) apparaît trop souvent par
    hasard et rangeait des articles retail dans "emailing".
    """
    t = text.lower()
    scores = {
        theme: sum(1 for kw in kws if kw in t)
        for theme, kws in THEME_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= min_score else default


def _is_ecom_relevant(text: str) -> bool:
    t = text.lower()
    if any(noise in t for noise in ECOM_NOISE):
        return False
    return any(kw in t for kw in ECOM_KEYWORDS)


# ── Dashboard actions e-commerce ─────────────────────────────────────────────

async def collect_dashboard() -> dict:
    """Performance du jour des actions e-commerce cotées (Yahoo Finance)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async def _fetch(client: httpx.AsyncClient, name: str, symbol: str):
        try:
            r = await client.get(
                YAHOO_CHART_URL.format(symbol=symbol),
                params={"interval": "1d", "range": "5d"}, timeout=8,
            )
            if r.status_code != 200:
                return None
            meta = r.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice") or 0
            prev = (
                meta.get("chartPreviousClose")
                or meta.get("regularMarketPreviousClose")
                or price
            )
            change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
            return {
                "nom": name, "ticker": symbol,
                "price": round(price, 2), "change_pct": change_pct,
            }
        except Exception as e:
            logger.debug(f"Ecom ticker {symbol}: {e}")
            return None

    stocks = []
    try:
        async with httpx.AsyncClient(headers=headers) as client:
            results = await asyncio.gather(
                *[_fetch(client, n, s) for n, s in ECOM_TICKERS.items()],
                return_exceptions=True,
            )
        stocks = [r for r in results if isinstance(r, dict) and r.get("price")]
        stocks.sort(key=lambda x: x["change_pct"], reverse=True)
    except Exception as e:
        logger.warning(f"collect_dashboard ecommerce erreur: {e}")

    dashboard = {"stocks": stocks}
    if stocks:
        changes = [s["change_pct"] for s in stocks]
        pct_up = round(sum(1 for c in changes if c > 0) / len(changes) * 100)
        dashboard["secteur"] = {
            "pct_hausse":  pct_up,
            "moyenne_pct": round(sum(changes) / len(changes), 2),
            "meilleur":    stocks[0],
            "pire":        stocks[-1],
            "sentiment":   "porteur" if pct_up >= 70 else "sous pression" if pct_up <= 30 else "mitigé",
        }
        logger.info(
            f"Dashboard e-commerce: {len(stocks)} actions, "
            f"{pct_up}% en hausse, moyenne {dashboard['secteur']['moyenne_pct']}%"
        )
    return dashboard


# ── Collecte news ────────────────────────────────────────────────────────────

async def collect_signals(hours: int = 48) -> list[dict]:
    """
    Collecte les nouveautés e-commerce et les classe par thème.

    Fenêtre par défaut 48h : la presse e-commerce publie moins vite que la
    presse crypto/marché, 24h laisserait des thèmes entiers à vide.
    """
    from utils.feeds import collect_feed_entries

    async def _one(feed: dict) -> list[dict]:
        entries = await collect_feed_entries(
            feed, hours=hours, sector="ecommerce",
            is_relevant=_is_ecom_relevant, max_entries=20,
        )
        for e in entries:
            e["theme"] = _classify_theme(
                f"{e['title']} {e['raw_content']}", default=feed.get("theme", "marketplace")
            )
        return entries

    results = await asyncio.gather(
        *[_one(f) for f in ECOM_NEWS_FEEDS], return_exceptions=True
    )

    signals = []
    for r in results:
        if isinstance(r, list):
            signals.extend(r)

    # Déduplication par URL puis par titre normalisé (Google News reprend les mêmes articles)
    seen_urls, seen_titles, unique = set(), set(), []
    for s in signals:
        key_title = "".join(c for c in s["title"].lower() if c.isalnum())[:60]
        if s["source_url"] in seen_urls or key_title in seen_titles:
            continue
        seen_urls.add(s["source_url"])
        seen_titles.add(key_title)
        unique.append(s)

    counts = {}
    for s in unique:
        counts[s["theme"]] = counts.get(s["theme"], 0) + 1
    logger.info(f"SCOUT-ECOMMERCE signaux: {len(unique)} news ({hours}h) — {counts}")
    return unique


# ── Point d'entrée principal ─────────────────────────────────────────────────

async def collect(hours: int = 48) -> dict:
    """
    Lance la collecte complète SCOUT-ECOMMERCE.
    Retourne : {dashboard: dict, signals: list[dict], themes: dict}
    """
    dashboard, signals = await asyncio.gather(
        collect_dashboard(),
        collect_signals(hours),
    )

    themes = {}
    for s in signals:
        themes[s.get("theme", "marketplace")] = themes.get(s.get("theme", "marketplace"), 0) + 1

    return {"dashboard": dashboard, "signals": signals, "themes": themes}
