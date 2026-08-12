"""
CORTEX — Collecte pour le mode "cowork".

Étape 1 sur 3 du rapport rédigé par Claude (voir COWORK.md) :

    1. cowork_collect.py   → ramasse les news, écrit un brief lisible
    2. l'agent Claude      → lit le brief, rédige l'analyse en JSON
    3. cowork_publish.py   → livre sur le dashboard et Telegram

Ce script ne fait AUCUN appel à un modèle : il ne demande que des flux RSS et
des cours de bourse publics. Il tourne donc dans le bac à sable de l'agent
cloud, qui n'a pas les clés Supabase/Telegram.

Sorties dans data/cowork/ :
  - collecte_AAAA-MM-JJ.md    le brief que l'agent lit
  - donnees_AAAA-MM-JJ.json   les chiffres exacts (dashboards), réinjectés
                              tels quels à la publication pour qu'aucun cours
                              de bourse ne soit retapé — donc jamais inventé
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("cowork.collect")

OUT_DIR = Path(__file__).parent / "data" / "cowork"

# Nombre de news proposées à l'agent par secteur. Assez large pour qu'il ait un
# vrai choix, assez court pour que le brief reste lisible d'un seul tenant.
PER_SECTOR = 22


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


def _fmt_crypto_dashboard(d: dict) -> str:
    if not d:
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
    if not d:
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
            out.append(f"- {key} : {item.get('value')} {item.get('unit','')} "
                       f"(précédent {item.get('prev')}, date {item.get('date')})")

    sectors = d.get("sectors", {})
    breadth = sectors.get("_breadth", {})
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


async def collect_all(hours: int = 24) -> tuple[str, dict]:
    """Lance les 5 scouts et retourne (brief markdown, données chiffrées)."""
    from agents.sources import titans, media, weak_signals, viral
    from agents import scout_crypto, scout_market, scout_deeptech, scout_ecommerce

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

    ai, crypto, market, deeptech, ecom = await asyncio.gather(
        _collect_ai(),
        scout_crypto.collect(hours),
        scout_market.collect(hours),
        scout_deeptech.collect(hours),
        scout_ecommerce.collect(max(hours, 48)),
        return_exceptions=True,
    )

    if isinstance(ai, Exception):       ai = []
    if isinstance(crypto, Exception):   crypto = {"dashboard": {}, "signals": []}
    if isinstance(market, Exception):   market = {"dashboard": {}, "signals": [], "hot_stocks": [], "crash": {}}
    if isinstance(deeptech, Exception): deeptech = []
    if isinstance(ecom, Exception):     ecom = {"dashboard": {}, "signals": [], "themes": {}}

    today = datetime.now().strftime("%Y-%m-%d")

    donnees = {
        "date": today,
        "crypto_dashboard": crypto.get("dashboard", {}),
        "market_dashboard": market.get("dashboard", {}),
        "market_hot_stocks": market.get("hot_stocks", []),
        "market_crash": market.get("crash", {}),
        "ecommerce_dashboard": ecom.get("dashboard", {}),
        "ecommerce_themes": ecom.get("themes", {}),
        "compte_news": {
            "ai": len(ai), "crypto": len(crypto.get("signals", [])),
            "market": len(market.get("signals", [])), "deeptech": len(deeptech),
            "ecommerce": len(ecom.get("signals", [])),
        },
    }

    brief = f"""# CORTEX — News collectées le {today}

Ce fichier est la matière première du rapport du matin. Il a été produit
automatiquement, sans aucun modèle de langage : ce sont les news brutes.

Ta mission : lire ces news, choisir les plus importantes, et rédiger l'analyse.
Les consignes de style et le format attendu sont dans COWORK.md, à la racine du
dépôt. Lis-le avant d'écrire quoi que ce soit.

Les chiffres ci-dessous (cours, indicateurs) sont donnés pour que tu comprennes
le contexte et que tu puisses les commenter. Tu n'as PAS à les recopier dans ton
rapport : ils y sont réinjectés automatiquement à la publication.

---

## 1. Intelligence artificielle — {len(ai)} news collectées

{_fmt_signals(ai, PER_SECTOR)}

---

## 2. Crypto & Web3 — {len(crypto.get('signals', []))} news collectées

### Données de marché du jour
{_fmt_crypto_dashboard(crypto.get('dashboard', {}))}

### News
{_fmt_signals(crypto.get('signals', []), PER_SECTOR)}

---

## 3. Marchés & Macro — {len(market.get('signals', []))} news collectées

### Données de marché du jour
{_fmt_market_dashboard(market.get('dashboard', {}))}

### News
{_fmt_signals(market.get('signals', []), PER_SECTOR)}

---

## 4. DeepTech & Ruptures — {len(deeptech)} news collectées

{_fmt_signals(deeptech, PER_SECTOR)}

---

## 5. E-commerce — {len(ecom.get('signals', []))} news collectées

Répartition par thème : {ecom.get('themes', {})}

### Actions du secteur aujourd'hui
{_fmt_ecom_dashboard(ecom.get('dashboard', {}))}

### News
{_fmt_signals(ecom.get('signals', []), PER_SECTOR + 8)}
"""

    return brief, donnees


async def main() -> int:
    hours = 24
    brief, donnees = await collect_all(hours)
    today = donnees["date"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    brief_path = OUT_DIR / f"collecte_{today}.md"
    data_path = OUT_DIR / f"donnees_{today}.json"

    brief_path.write_text(brief, encoding="utf-8")
    data_path.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"Brief écrit : {brief_path} ({len(brief):,} caractères)")
    logger.info(f"Chiffres écrits : {data_path}")
    logger.info(f"News par secteur : {donnees['compte_news']}")

    total = sum(donnees["compte_news"].values())
    if total < 10:
        logger.error(f"Collecte anormalement faible ({total} news) — vérifier les flux")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
