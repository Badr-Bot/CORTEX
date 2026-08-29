"""
CORTEX — Collecte pour le mode "cowork".

Étape 1 sur 3 du rapport rédigé par Claude (voir COWORK.md) :

    1. cowork_collect.py   → ramasse les news + outils, écrit un brief lisible
    2. l'agent Claude      → lit le brief, rédige l'analyse en JSON
    3. cowork_publish.py   → livre sur le dashboard et Telegram

Ce script ne fait AUCUN appel à un modèle : il ne demande que des flux RSS,
des API publiques et des cours de bourse.

OÙ IL TOURNE : dans GitHub Actions (.github/workflows/cowork_collect.yml), qui
a un accès réseau complet, et qui commit le résultat dans le dépôt. Le bac à
sable de l'agent cloud bloque presque tout le réseau sortant (403 "egress
blocked") : y lancer ce script ne ramène rien. L'agent lit donc simplement les
fichiers déjà commités.

Sorties dans data/cowork/ :
  - collecte_AAAA-MM-JJ.md    le brief que l'agent lit
  - donnees_AAAA-MM-JJ.json   les chiffres exacts (dashboards), réinjectés
                              tels quels à la publication pour qu'aucun cours
                              de bourse ne soit retapé — donc jamais inventé

Usage :
    python cowork_collect.py [--date AAAA-MM-JJ] [--hours 30] [--force]

--date  : date du rapport que cette collecte alimente (défaut : aujourd'hui UTC).
          Lancé la veille au soir, on passe la date du lendemain.
--force : écraser même si une collecte plus riche existe déjà pour cette date.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("cowork.collect")

OUT_DIR = Path(__file__).parent / "data" / "cowork"

# Nombre d'entrées proposées à l'agent par section. Assez large pour qu'il ait
# un vrai choix (Badr veut "plus d'infos"), assez court pour rester lisible.
PER_SECTOR = 30
TRENDING_MAX = 20
TOOLS_MAX = 30

# En dessous, la collecte est considérée comme cassée (réseau, flux morts).
MIN_NEWS_VALIDE = 10

USAGE_LABELS = {
    "video":           "générer des vidéos / créas",
    "produit_gagnant": "trouver un produit gagnant",
    "analyse_marche":  "analyser un marché / la concurrence",
    "scraping":        "scraper des données",
    "pub":             "pubs Meta / TikTok / Google",
    "fiches_produit":  "fiches et visuels produit",
    "service_client":  "service client",
    "skill_claude":    "skill / plugin Claude",
    "automatisation":  "automatisation boutique",
}


def _fmt_signals(signals: list[dict], limit: int) -> str:
    lines = []
    for i, s in enumerate(signals[:limit], 1):
        title = (s.get("title") or "").strip()
        src = s.get("source_name", "?")
        url = s.get("source_url", "")
        content = " ".join((s.get("raw_content") or "").split())[:280]
        theme = s.get("theme")
        tag = f" [thème: {theme}]" if theme else ""
        lines.append(f"{i}. **{title}**{tag}\n   - source : {src}\n   - lien : {url}\n   - résumé : {content}")
    return "\n\n".join(lines) if lines else "_Aucune news collectée pour ce secteur._"


def _fmt_tools(tools: list[dict], limit: int) -> str:
    lines = []
    for i, t in enumerate(tools[:limit], 1):
        usage = t.get("usage", "automatisation")
        label = USAGE_LABELS.get(usage, usage)
        prix = "gratuit / open source" if t.get("gratuit", True) else "payant ou freemium"
        content = " ".join((t.get("raw_content") or "").split())[:280]
        lines.append(
            f"{i}. **{t.get('title', '')}** [usage: {usage} — {label}] [{prix}]\n"
            f"   - source : {t.get('source_name', '?')}\n"
            f"   - lien : {t.get('source_url', '')}\n"
            f"   - résumé : {content}"
        )
    return "\n\n".join(lines) if lines else "_Aucun outil repéré aujourd'hui._"


def is_trending_item(s: dict) -> bool:
    """Repos GitHub et modèles Hugging Face — à part des news."""
    src = (s.get("source_name") or "")
    return s.get("category") in ("viral", "weak_signal") and src.startswith(("GitHub", "HuggingFace"))


# Ce qui "monte" d'abord (repos émergents, trending récent, modèles), les géants
# établis (transformers, AutoGPT…) en dernier et plafonnés : ils ne bougent pas.
_TRENDING_SOURCE_RANK = {"GitHub Émergent": 0, "GitHub Trending": 1, "HuggingFace": 2, "GitHub Viral": 3}
_MAX_GIANTS = 5


def order_trending(items: list[dict]) -> list[dict]:
    def rank(s: dict) -> int:
        src = s.get("source_name") or ""
        for prefix, r in _TRENDING_SOURCE_RANK.items():
            if src.startswith(prefix):
                return r
        return 2
    ordered = sorted(items, key=lambda s: (rank(s), -(s.get("stars_count") or 0)))
    giants = 0
    out = []
    for s in ordered:
        if (s.get("source_name") or "").startswith("GitHub Viral"):
            giants += 1
            if giants > _MAX_GIANTS:
                continue
        out.append(s)
    return out


def _fmt_crypto_dashboard(d: dict) -> str:
    if not d or not d.get("btc_price"):
        return "_indisponible_"
    cycle = d.get("cycle", {})
    return "\n".join([
        f"- Prix BTC : ${d.get('btc_price', 0):,} ({d.get('btc_change_24h', '?')}% sur 24h)",
        f"- Dominance BTC : {d.get('btc_dominance', '?')}%",
        f"- Fear & Greed : {d.get('fear_greed_score', '?')} — {d.get('fear_greed_label', '?')} "
        f"(tendance {d.get('fear_greed_trend', '?')}, moyenne 7j {d.get('fear_greed_avg_7d', '?')})",
        f"- Funding rate : {d.get('funding_description', '?')}",
        f"- Ratio long/short : {d.get('long_short_ratio', '?')}",
        f"- Frais réseau BTC : {d.get('mempool_fee', '?')} sat/vB",
        f"- Phase de cycle détectée : {cycle.get('phase', '?')} — {cycle.get('conseil', '')}",
        f"- Flux d'échanges : {d.get('exchange_flows', {}).get('trend', '?')}",
        f"- Variation capitalisation totale 24h : {d.get('market_cap_change', '?')}%",
    ])


def _fmt_market_dashboard(d: dict) -> str:
    if not d or not d.get("sp500", {}).get("price") or d["sp500"]["price"] == "N/A":
        return "_indisponible_"

    def line(key, label):
        item = d.get(key, {})
        if not item:
            return f"- {label} : indisponible"
        return f"- {label} : {item.get('price', '?')} ({item.get('change_pct', 0):+.1f}%)"

    out = [
        line("sp500", "S&P 500"), line("nasdaq", "Nasdaq"), line("gold", "Or"),
        line("oil", "Pétrole"), line("dxy", "Dollar (DXY)"),
        f"- VIX : {d.get('vix', {}).get('price', '?')} — {d.get('vix', {}).get('interpretation', '?')}",
        f"- Taux US 10 ans : {d.get('us_10y', {}).get('price', '?')} ({d.get('us_10y', {}).get('change_bps', '?')})",
    ]

    fred = d.get("fred", {})
    if fred:
        out.append("\nIndicateurs macro officiels (FRED) :")
        for key, item in fred.items():
            out.append(f"- {key} : {item.get('value')} {item.get('unit', '')} "
                       f"(précédent {item.get('prev')}, date {item.get('date')})")

    breadth = d.get("sectors", {}).get("_breadth", {})
    if breadth:
        out.append(
            f"\nSecteurs : {breadth.get('pct_secteurs_hausse')}% en hausse — "
            f"meilleur {breadth.get('meilleur', {}).get('nom')} "
            f"({breadth.get('meilleur', {}).get('change_pct')}%), "
            f"pire {breadth.get('pire', {}).get('nom')} "
            f"({breadth.get('pire', {}).get('change_pct')}%)"
        )

    insiders = d.get("insider_buys", [])[:5]
    if insiders:
        out.append("\nAchats d'initiés récents (> 100 000 $) :")
        for t in insiders:
            out.append(f"- {t.get('ticker')} — {t.get('insider')} — {t.get('value_usd'):,} $ le {t.get('date')}")

    earnings = d.get("earnings_week", [])[:6]
    if earnings:
        out.append("\nRésultats d'entreprises attendus cette semaine :")
        for e in earnings:
            out.append(f"- {e.get('ticker')} le {e.get('date')} (dans {e.get('days_until')} jours)")

    return "\n".join(out)


def _fmt_ecom_dashboard(d: dict) -> str:
    stocks = d.get("stocks", [])
    if not stocks:
        return "_indisponible_"
    out = [f"- {s['nom']} ({s['ticker']}) : {s['price']} ({s['change_pct']:+.1f}%)" for s in stocks]
    sect = d.get("secteur", {})
    if sect:
        out.append(f"\nSecteur : {sect.get('pct_hausse')}% des actions en hausse — {sect.get('sentiment')}")
    return "\n".join(out)


async def collect_all(hours: int = 30, date: str | None = None) -> tuple[str, dict]:
    """Lance les 6 scouts et retourne (brief markdown, données chiffrées)."""
    from agents.sources import titans, media, weak_signals, viral
    from agents import scout_crypto, scout_market, scout_deeptech, scout_ecommerce, scout_tools

    async def _collect_ai():
        results = await asyncio.gather(
            titans.collect(hours), media.collect(hours),
            weak_signals.collect(hours), viral.collect(hours),
            return_exceptions=True,
        )
        seen, unique = set(), []
        for r in results:
            if isinstance(r, list):
                for s in r:
                    url = s.get("source_url", "")
                    if url and url not in seen:
                        seen.add(url)
                        unique.append(s)
        return unique

    ai, crypto, market, deeptech, ecom, tools = await asyncio.gather(
        _collect_ai(),
        scout_crypto.collect(hours),
        scout_market.collect(hours),
        scout_deeptech.collect(hours),
        scout_ecommerce.collect(max(hours, 48)),
        scout_tools.collect(72),
        return_exceptions=True,
    )

    if isinstance(ai, Exception):       ai = []
    if isinstance(crypto, Exception):   crypto = {"dashboard": {}, "signals": []}
    if isinstance(market, Exception):   market = {"dashboard": {}, "signals": [], "hot_stocks": [], "crash": {}}
    if isinstance(deeptech, Exception): deeptech = []
    if isinstance(ecom, Exception):     ecom = {"dashboard": {}, "signals": [], "themes": {}}
    if isinstance(tools, Exception):    tools = {"tools": [], "usages": {}}

    trending = order_trending([s for s in ai if is_trending_item(s)])
    ai_news = [s for s in ai if not is_trending_item(s)]

    report_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    donnees = {
        "date": report_date,
        "collecte_le": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "crypto_dashboard": crypto.get("dashboard", {}),
        "market_dashboard": market.get("dashboard", {}),
        "market_hot_stocks": market.get("hot_stocks", []),
        "market_crash": market.get("crash", {}),
        "ecommerce_dashboard": ecom.get("dashboard", {}),
        "ecommerce_themes": ecom.get("themes", {}),
        "outils_usages": tools.get("usages", {}),
        "compte_news": {
            "ai": len(ai_news), "trending": len(trending),
            "crypto": len(crypto.get("signals", [])),
            "market": len(market.get("signals", [])), "deeptech": len(deeptech),
            "ecommerce": len(ecom.get("signals", [])),
            "outils": len(tools.get("tools", [])),
        },
    }

    brief = f"""# CORTEX — News collectées pour le rapport du {report_date}

Ce fichier est la matière première du rapport du matin. Il a été produit
automatiquement, sans aucun modèle de langage : ce sont les news brutes.
Collecte effectuée le {donnees['collecte_le']}.

Ta mission : lire ces news, choisir les plus importantes, et rédiger l'analyse.
Les consignes de style et le format attendu sont dans COWORK.md, à la racine du
dépôt. Lis-le avant d'écrire quoi que ce soit.

Les chiffres ci-dessous (cours, indicateurs) sont donnés pour que tu comprennes
le contexte et que tu puisses les commenter. Tu n'as PAS à les recopier dans ton
rapport : ils y sont réinjectés automatiquement à la publication.

---

## 1. Intelligence artificielle — {len(ai_news)} news collectées

{_fmt_signals(ai_news, PER_SECTOR)}

---

## 2. Repos GitHub et modèles qui montent — {len(trending)} repérés

Ce sont les projets open source et modèles IA les plus populaires du moment.
Sert à remplir `ai.trending_repos` : explique à Badr ce que c'est et à quoi ça
peut lui servir concrètement (ou pourquoi c'est juste bon à savoir).

{_fmt_signals(trending, TRENDING_MAX)}

---

## 3. Crypto & Web3 — {len(crypto.get('signals', []))} news collectées

### Données de marché du jour
{_fmt_crypto_dashboard(crypto.get('dashboard', {}))}

### News
{_fmt_signals(crypto.get('signals', []), PER_SECTOR)}

---

## 4. Marchés & Macro — {len(market.get('signals', []))} news collectées

### Données de marché du jour
{_fmt_market_dashboard(market.get('dashboard', {}))}

### News
{_fmt_signals(market.get('signals', []), PER_SECTOR)}

---

## 5. DeepTech & Ruptures — {len(deeptech)} news collectées

{_fmt_signals(deeptech, PER_SECTOR)}

---

## 6. E-commerce — {len(ecom.get('signals', []))} news collectées

Répartition par thème : {ecom.get('themes', {})}

### Actions du secteur aujourd'hui
{_fmt_ecom_dashboard(ecom.get('dashboard', {}))}

### News
{_fmt_signals(ecom.get('signals', []), PER_SECTOR + 8)}

---

## 7. Boîte à outils e-commerce — {len(tools.get('tools', []))} outils repérés

Répartition par usage : {tools.get('usages', {})}

Sert à remplir `ecommerce.outils` : des outils concrets (repo à cloner, skill
Claude à activer, modèle à essayer, app à tester) pour générer des vidéos,
trouver un produit gagnant, analyser un marché, scraper, automatiser les pubs.

{_fmt_tools(tools.get('tools', []), TOOLS_MAX)}
"""

    return brief, donnees


def news_count(donnees: dict) -> int:
    return sum(donnees.get("compte_news", {}).values())


def existing_count(data_path: Path) -> int:
    """Nombre d'entrées d'une collecte déjà commitée pour cette date (0 si aucune)."""
    if not data_path.exists():
        return 0
    try:
        return news_count(json.loads(data_path.read_text(encoding="utf-8")))
    except Exception:
        return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=None, help="date du rapport alimenté (AAAA-MM-JJ)")
    parser.add_argument("--hours", type=int, default=30, help="fenêtre de collecte en heures")
    parser.add_argument("--force", action="store_true", help="écraser une collecte plus riche")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    brief, donnees = await collect_all(args.hours, args.date)
    date = donnees["date"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    brief_path = OUT_DIR / f"collecte_{date}.md"
    data_path = OUT_DIR / f"donnees_{date}.json"

    total = news_count(donnees)
    deja = existing_count(data_path)
    if deja > total and not args.force:
        logger.warning(
            f"Collecte existante plus riche pour le {date} ({deja} entrées > {total}) — conservée. "
            "Utilise --force pour écraser."
        )
        return 0

    brief_path.write_text(brief, encoding="utf-8")
    data_path.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"Brief écrit : {brief_path} ({len(brief):,} caractères)")
    logger.info(f"Chiffres écrits : {data_path}")
    logger.info(f"Entrées par section : {donnees['compte_news']}")

    if total < MIN_NEWS_VALIDE:
        logger.error(f"Collecte anormalement faible ({total} entrées) — vérifier le réseau et les flux")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
