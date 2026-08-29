"""
CORTEX — Validation du rapport rédigé en mode cowork.

Étape 2,5 sur 3 : l'agent Claude lance ce script après avoir écrit son rapport,
et corrige jusqu'à ce qu'il passe au vert. Il vérifie ce qu'un modèle peut rater :

  - structure et valeurs autorisées (le dashboard casse si un champ manque)
  - longueurs minimales (un "fait" de 3 lignes n'explique rien)
  - **URLs réellement présentes dans la collecte du jour** — c'est le garde-fou
    contre la source inventée, la faute la plus grave possible ici
  - les chiffres du jour (donnees_*.json) : s'ils sont vides, le dashboard
    affichera "N/A" partout — avertissement bloquant pour la lecture, pas pour
    la publication

Usage :
    python cowork_check.py [AAAA-MM-JJ]
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

COWORK_DIR = Path(__file__).parent / "data" / "cowork"

SIZINGS = {"Fort", "Moyen", "Faible"}
STATUSES = {"green", "yellow", "red"}
REGIMES = {"Risk-on", "Risk-off", "Inflation trade", "Stagflation", "Transition"}
DIRECTIONS = {"BULLISH", "NEUTRE-BULLISH", "NEUTRE", "NEUTRE-BEARISH", "BEARISH"}
MAGNITUDES = {"forte", "modérée", "faible"}
ECOM_THEMES = {"marketplace", "automation", "emailing", "creatives", "operations"}
DEEPTECH_HORIZONS = {"5-10", "10+"}
TRENDING_TYPES = {"repo", "modele", "space"}
# Doit rester aligné sur agents.scout_tools.USAGES (testé dans test_cowork.py)
TOOL_CATEGORIES = {
    "video", "produit_gagnant", "analyse_marche", "scraping", "pub",
    "fiches_produit", "service_client", "skill_claude", "automatisation",
}
RECESSION_KEYS = [
    "courbe_taux", "emploi", "ism_manuf", "ism_services", "conso_conf",
    "credit_spread", "earnings_rev", "pmi_composite", "retail_sales", "housing",
]

# Combien de signaux approfondis par section (min, max)
SIGNAL_RANGE = {
    "ai": (3, 5), "crypto": (3, 5), "market": (3, 5), "deeptech": (2, 4), "ecommerce": (3, 5),
}
MIN_AUTRES_NEWS = 4
MIN_TRENDING = 3
MIN_OUTILS = 3

SIGNAL_FIELDS = [
    "conviction", "title", "en_clair", "fait", "implication_2", "implication_3",
    "action", "sizing", "invalide_si", "source_name", "source_url",
]

MIN_LENGTHS = {"en_clair": 60, "fait": 400, "implication_2": 120, "implication_3": 120, "action": 60}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _collect_urls(brief_path: Path) -> set[str]:
    if not brief_path.exists():
        return set()
    return set(re.findall(r"https?://\S+", brief_path.read_text(encoding="utf-8")))


def _has_markdown(value) -> bool:
    return isinstance(value, str) and ("**" in value or value.lstrip().startswith("#"))


def _check_url(url: str, where: str, known_urls: set[str], r: Report) -> None:
    if url and known_urls and url not in known_urls:
        r.err(f"{where} : source_url absente de la collecte du jour — source inventée ? {url}")


def _check_signal(sig: dict, where: str, known_urls: set[str], r: Report, deeptech: bool = False) -> None:
    if not isinstance(sig, dict):
        r.err(f"{where} : ce n'est pas un objet JSON")
        return

    for field in SIGNAL_FIELDS:
        if not sig.get(field) and sig.get(field) != 0:
            r.err(f"{where} : champ '{field}' manquant ou vide")

    conviction = sig.get("conviction")
    if not isinstance(conviction, int) or not 1 <= conviction <= 5:
        r.err(f"{where} : conviction doit être un entier de 1 à 5 (reçu {conviction!r})")

    if sig.get("sizing") not in SIZINGS:
        r.err(f"{where} : sizing invalide ({sig.get('sizing')!r}) — attendu {sorted(SIZINGS)}")

    for field, minimum in MIN_LENGTHS.items():
        value = sig.get(field) or ""
        if isinstance(value, str) and 0 < len(value) < minimum:
            r.err(f"{where} : '{field}' trop court ({len(value)} caractères, minimum {minimum}) — développe")

    title = sig.get("title") or ""
    if title and title != title.upper():
        r.warn(f"{where} : le titre devrait être en majuscules")
    if len(title) > 90:
        r.warn(f"{where} : titre un peu long ({len(title)} caractères)")

    for field in ("fait", "implication_2", "implication_3", "en_clair", "action"):
        if _has_markdown(sig.get(field) or ""):
            r.err(f"{where} : '{field}' contient du markdown — texte brut uniquement")

    _check_url(sig.get("source_url") or "", where, known_urls, r)

    if deeptech:
        if sig.get("horizon") not in DEEPTECH_HORIZONS:
            r.err(f"{where} : horizon deeptech invalide ({sig.get('horizon')!r}) — attendu '5-10' ou '10+'")
        score = sig.get("credibilite_score")
        if not isinstance(score, int) or not 0 <= score <= 4:
            r.err(f"{where} : credibilite_score doit être un entier de 0 à 4")


def _check_signals(section: dict, sector: str, known_urls: set[str], r: Report) -> None:
    signals = section.get("signals", [])
    lo, hi = SIGNAL_RANGE[sector]
    if not lo <= len(signals) <= hi:
        r.err(f"{sector}.signals : entre {lo} et {hi} signaux attendus, {len(signals)} trouvés")
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"{sector}.signals[{i}]", known_urls, r, deeptech=(sector == "deeptech"))


def _check_autres_news(section: dict, sector: str, known_urls: set[str], r: Report) -> None:
    """Les autres news du jour, en une phrase simple chacune."""
    items = section.get("autres_news")
    if not isinstance(items, list) or len(items) < MIN_AUTRES_NEWS:
        r.warn(f"{sector}.autres_news : au moins {MIN_AUTRES_NEWS} news attendues "
               f"({len(items) if isinstance(items, list) else 0} trouvées) — Badr veut voir plus de news")
        items = items if isinstance(items, list) else []
    for i, item in enumerate(items, 1):
        where = f"{sector}.autres_news[{i}]"
        if not isinstance(item, dict):
            r.err(f"{where} : ce n'est pas un objet JSON")
            continue
        for field in ("titre", "en_clair", "source_name", "source_url"):
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        en_clair = item.get("en_clair") or ""
        if 0 < len(en_clair) < 40:
            r.err(f"{where} : 'en_clair' trop court ({len(en_clair)} caractères) — explique en une vraie phrase")
        if _has_markdown(en_clair):
            r.err(f"{where} : 'en_clair' contient du markdown")
        _check_url(item.get("source_url") or "", where, known_urls, r)


def _check_trending(ai: dict, known_urls: set[str], r: Report) -> None:
    items = ai.get("trending_repos")
    if not isinstance(items, list) or len(items) < MIN_TRENDING:
        r.warn(f"ai.trending_repos : au moins {MIN_TRENDING} repos/modèles attendus "
               f"({len(items) if isinstance(items, list) else 0} trouvés)")
        items = items if isinstance(items, list) else []
    for i, item in enumerate(items, 1):
        where = f"ai.trending_repos[{i}]"
        if not isinstance(item, dict):
            r.err(f"{where} : ce n'est pas un objet JSON")
            continue
        for field in ("nom", "quoi", "pour_toi", "source_url"):
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        if item.get("type") not in TRENDING_TYPES:
            r.err(f"{where} : type invalide ({item.get('type')!r}) — attendu {sorted(TRENDING_TYPES)}")
        _check_url(item.get("source_url") or "", where, known_urls, r)


def _check_outils(ecom: dict, known_urls: set[str], r: Report) -> None:
    items = ecom.get("outils")
    if not isinstance(items, list) or len(items) < MIN_OUTILS:
        r.warn(f"ecommerce.outils : au moins {MIN_OUTILS} outils attendus "
               f"({len(items) if isinstance(items, list) else 0} trouvés) — c'est la section que Badr attend le plus")
        items = items if isinstance(items, list) else []
    for i, item in enumerate(items, 1):
        where = f"ecommerce.outils[{i}]"
        if not isinstance(item, dict):
            r.err(f"{where} : ce n'est pas un objet JSON")
            continue
        for field in ("nom", "quoi", "pour_toi", "comment_tester", "source_url"):
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        if item.get("categorie") not in TOOL_CATEGORIES:
            r.err(f"{where} : categorie invalide ({item.get('categorie')!r}) — attendu {sorted(TOOL_CATEGORIES)}")
        if "gratuit" in item and not isinstance(item["gratuit"], bool):
            r.err(f"{where} : 'gratuit' doit être true ou false")
        _check_url(item.get("source_url") or "", where, known_urls, r)


RADAR_FIELDS = [
    "produit", "boutique", "statut", "signal", "stade_marche", "notoriete", "ca_jour_estime",
    "difficulte", "difficulte_pourquoi", "marche_fr", "ou_lancer", "verdict", "verdict_pourquoi",
    "budget_test", "lien_boutique",
]
RADAR_STATUTS = {"BANGER", "EXPLOSE", "SANS TRAFIC", "A SURVEILLER"}
RADAR_DIFFICULTES = {"facile", "moyen", "difficile"}
RADAR_MARCHES = {"LIBRE", "PRIS", "PARTIEL", "A VERIFIER"}
RADAR_VERDICTS = {"GO TEST", "A SURVEILLER", "ECARTER"}


def _check_radar(ecom: dict, r: Report) -> None:
    """Produits du radar TrendTrack : facultatif, mais s'il est là, complet
    et honnête (docs/RADAR.md §6)."""
    items = ecom.get("radar_produits")
    if items is None:
        r.warn("ecommerce.radar_produits absent — mets [] si le radar n'a pas tourné")
        return
    if not isinstance(items, list):
        r.err("ecommerce.radar_produits doit être une liste")
        return
    for i, item in enumerate(items, 1):
        where = f"ecommerce.radar_produits[{i}]"
        if not isinstance(item, dict):
            r.err(f"{where} : ce n'est pas un objet JSON")
            continue
        for field in RADAR_FIELDS:
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        if item.get("statut") not in RADAR_STATUTS:
            r.err(f"{where} : statut invalide ({item.get('statut')!r}) — attendu {sorted(RADAR_STATUTS)}")
        if item.get("difficulte") not in RADAR_DIFFICULTES:
            r.err(f"{where} : difficulte invalide ({item.get('difficulte')!r}) — attendu {sorted(RADAR_DIFFICULTES)}")
        if item.get("marche_fr") not in RADAR_MARCHES:
            r.err(f"{where} : marche_fr invalide ({item.get('marche_fr')!r}) — attendu {sorted(RADAR_MARCHES)}")
        elif item.get("marche_fr") == "LIBRE" and not item.get("marche_fr_detail"):
            r.err(f"{where} : marche_fr = LIBRE sans marche_fr_detail — un 0 résultat s'écrit A VERIFIER, "
                  "LIBRE exige la preuve (requête search_ads trend_signal=reach)")
        elif item.get("marche_fr") == "PRIS":
            marches = item.get("marches") or {}
            ouverts = [m for m, etat in marches.items() if m != "FR" and etat in ("LIBRE", "PARTIEL")]
            if not ouverts:
                r.err(f"{where} : marche_fr = PRIS et aucun autre marché de Badr (DE/ES/GB) vérifié LIBRE ou PARTIEL "
                      "dans 'marches' — « personne ne l'a lancé sur ton marché » (MASTER RESEARCH · 3) : "
                      "contrôle DE/ES/GB ou écarte-le")
            elif not item.get("ou_lancer"):
                r.err(f"{where} : marché FR pris mais {ouverts} ouvert(s) — 'ou_lancer' doit le dire")
        marches = item.get("marches")
        if marches is not None:
            if not isinstance(marches, dict) or any(v not in RADAR_MARCHES for v in marches.values()):
                r.err(f"{where} : 'marches' doit être un objet {{FR/DE/ES/GB: LIBRE|PRIS|PARTIEL|A VERIFIER}}")
        if item.get("statut") not in RADAR_STATUTS - {"A SURVEILLER"} and item.get("verdict") == "GO TEST":
            r.warn(f"{where} : GO TEST sur un statut {item.get('statut')} — vérifie que le signal explose vraiment")
        if item.get("verdict") not in RADAR_VERDICTS:
            r.err(f"{where} : verdict invalide ({item.get('verdict')!r}) — attendu {sorted(RADAR_VERDICTS)}")
        ca = item.get("ca_jour_estime") or ""
        if ca and "estim" not in ca.lower() and "non estimable" not in ca.lower():
            r.err(f"{where} : ca_jour_estime doit être étiqueté estimation (ou 'non estimable')")
        for field in ("criteres_ok", "criteres_ko"):
            if field in item and not isinstance(item[field], list):
                r.err(f"{where} : '{field}' doit être une liste")
        for field in ("lien_boutique", "lien_adlibrary"):
            url = item.get(field) or ""
            if url and not url.startswith("http"):
                r.err(f"{where} : {field} invalide ({url})")

    ecartes = ecom.get("radar_ecartes")
    if ecartes is not None:
        if not isinstance(ecartes, list):
            r.err("ecommerce.radar_ecartes doit être une liste")
        else:
            for i, item in enumerate(ecartes, 1):
                if not isinstance(item, dict) or not all(item.get(k) for k in ("produit", "boutique", "raison")):
                    r.err(f"ecommerce.radar_ecartes[{i}] : produit, boutique et raison obligatoires")
    if isinstance(items, list) and not items and not ecartes:
        r.warn("ecommerce.radar_produits vide sans radar_ecartes — dis ce qui a été vérifié et pourquoi rien ne passe")


def check(report: dict, known_urls: set[str]) -> Report:
    r = Report()

    for sector in ("ai", "crypto", "market", "deeptech", "ecommerce"):
        if sector not in report:
            r.err(f"Section '{sector}' absente du rapport")

    # ── IA ────────────────────────────────────────────────────────────────────
    ai = report.get("ai", {})
    _check_signals(ai, "ai", known_urls, r)
    if not 2 <= len(ai.get("watchlist", [])) <= 3:
        r.warn(f"ai.watchlist : 2 à 3 items attendus, {len(ai.get('watchlist', []))} trouvés")
    _check_trending(ai, known_urls, r)
    _check_autres_news(ai, "ai", known_urls, r)

    # ── Crypto ────────────────────────────────────────────────────────────────
    crypto = report.get("crypto", {})
    if crypto.get("direction") not in DIRECTIONS:
        r.err(f"crypto.direction invalide ({crypto.get('direction')!r})")
    if crypto.get("magnitude") not in MAGNITUDES:
        r.err(f"crypto.magnitude invalide ({crypto.get('magnitude')!r})")
    if not crypto.get("phase"):
        r.err("crypto.phase manquante")
    if not crypto.get("bear_case"):
        r.err("crypto.bear_case manquant")

    score = crypto.get("score", {})
    for key in ("onchain", "cycle", "macro", "sentiment", "momentum"):
        item = score.get(key)
        if not isinstance(item, dict):
            r.err(f"crypto.score.{key} manquant")
            continue
        if not isinstance(item.get("value"), int) or not -2 <= item["value"] <= 2:
            r.err(f"crypto.score.{key}.value doit être un entier de -2 à +2")
        note = item.get("note") or ""
        if not note or note.strip().upper() == "N/A":
            r.err(f"crypto.score.{key}.note vide ou 'N/A' — justifie avec des données")

    _check_signals(crypto, "crypto", known_urls, r)
    if len(crypto.get("trending_alts", [])) != 3:
        r.warn(f"crypto.trending_alts : 3 attendus, {len(crypto.get('trending_alts', []))} trouvés")
    _check_autres_news(crypto, "crypto", known_urls, r)

    # ── Marchés ───────────────────────────────────────────────────────────────
    market = report.get("market", {})
    indicators = market.get("recession_indicators", {})
    missing = [k for k in RECESSION_KEYS if k not in indicators]
    if missing:
        r.err(f"market.recession_indicators : indicateurs manquants {missing}")
    for key, item in indicators.items():
        if not isinstance(item, dict) or item.get("status") not in STATUSES:
            r.err(f"market.recession_indicators.{key}.status invalide — attendu green/yellow/red")
        elif not item.get("note"):
            r.err(f"market.recession_indicators.{key}.note vide")

    if market.get("regime") not in REGIMES:
        r.err(f"market.regime invalide ({market.get('regime')!r}) — attendu {sorted(REGIMES)}")
    if not market.get("regime_justification"):
        r.err("market.regime_justification manquante")
    rec_score = market.get("recession_score")
    if not isinstance(rec_score, (int, float)) or not 0 <= rec_score <= 10:
        r.err(f"market.recession_score doit être un nombre de 0 à 10 (reçu {rec_score!r})")

    _check_signals(market, "market", known_urls, r)
    _check_autres_news(market, "market", known_urls, r)

    # ── DeepTech ──────────────────────────────────────────────────────────────
    deeptech = report.get("deeptech", {})
    _check_signals(deeptech, "deeptech", known_urls, r)
    _check_autres_news(deeptech, "deeptech", known_urls, r)

    # ── E-commerce ────────────────────────────────────────────────────────────
    ecom = report.get("ecommerce", {})
    if not ecom.get("tendance_globale"):
        r.err("ecommerce.tendance_globale manquante")

    nouveautes = ecom.get("nouveautes", [])
    if not 3 <= len(nouveautes) <= 6:
        r.err(f"ecommerce.nouveautes : 3 à 6 attendues, {len(nouveautes)} trouvées")
    for i, item in enumerate(nouveautes, 1):
        where = f"ecommerce.nouveautes[{i}]"
        if item.get("theme") not in ECOM_THEMES:
            r.err(f"{where} : theme invalide ({item.get('theme')!r}) — attendu {sorted(ECOM_THEMES)}")
        for field in ("titre", "quoi", "pourquoi", "source_url"):
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        _check_url(item.get("source_url") or "", where, known_urls, r)

    _check_signals(ecom, "ecommerce", known_urls, r)
    themes = []
    for i, sig in enumerate(ecom.get("signals", []), 1):
        theme = sig.get("theme") if isinstance(sig, dict) else None
        if theme not in ECOM_THEMES:
            r.err(f"ecommerce.signals[{i}] : theme invalide ({theme!r})")
        else:
            themes.append(theme)
    if len(set(themes)) < min(len(themes), 3):
        r.err("ecommerce.signals : les 3 premiers signaux doivent porter sur 3 thèmes DIFFÉRENTS")

    _check_outils(ecom, known_urls, r)
    _check_radar(ecom, r)
    _check_autres_news(ecom, "ecommerce", known_urls, r)

    if len(ecom.get("actions_semaine", [])) != 2:
        r.err(f"ecommerce.actions_semaine : 2 attendues, {len(ecom.get('actions_semaine', []))} trouvées")

    return r


def check_donnees(donnees: dict) -> list[str]:
    """Avertissements si les chiffres du jour sont vides (collecte sans réseau)."""
    warnings = []
    if not donnees:
        return ["Aucun fichier de chiffres (donnees_*.json) : tous les tableaux de bord seront vides"]
    if not donnees.get("crypto_dashboard", {}).get("btc_price"):
        warnings.append("Chiffres crypto vides (prix BTC = 0) — le tableau de bord crypto affichera N/A")
    sp = donnees.get("market_dashboard", {}).get("sp500", {})
    if not sp or sp.get("price") in (None, "N/A", 0):
        warnings.append("Chiffres marchés vides (S&P 500 = N/A) — le tableau de bord marchés affichera N/A")
    if not donnees.get("ecommerce_dashboard", {}).get("stocks"):
        warnings.append("Actions e-commerce vides — la grille des actions du secteur sera absente")
    return warnings


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    report_path = COWORK_DIR / f"rapport_{date}.json"
    brief_path = COWORK_DIR / f"collecte_{date}.md"
    data_path = COWORK_DIR / f"donnees_{date}.json"

    if not report_path.exists():
        print(f"ERREUR : {report_path} introuvable.")
        print("Écris d'abord le rapport, en suivant COWORK.md.")
        return 1

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERREUR : JSON invalide dans {report_path.name} — ligne {e.lineno}, colonne {e.colno}")
        print(f"  {e.msg}")
        return 1

    known_urls = _collect_urls(brief_path)
    if not known_urls:
        print(f"AVERTISSEMENT : collecte {brief_path.name} introuvable — les URLs ne seront pas vérifiées.")

    donnees = {}
    if data_path.exists():
        try:
            donnees = json.loads(data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            donnees = {}
    for w in check_donnees(donnees):
        print(f"  avertissement chiffres : {w}")

    r = check(report, known_urls)

    for w in r.warnings:
        print(f"  avertissement : {w}")

    if r.errors:
        print(f"\n{len(r.errors)} ERREUR(S) — corrige puis relance :\n")
        for e in r.errors:
            print(f"  - {e}")
        return 1

    total = sum(len(report.get(s, {}).get("signals", [])) for s in
                ("ai", "crypto", "market", "deeptech", "ecommerce"))
    autres = sum(len(report.get(s, {}).get("autres_news", []) or []) for s in
                 ("ai", "crypto", "market", "deeptech", "ecommerce"))
    outils = len(report.get("ecommerce", {}).get("outils", []) or [])
    print(f"\nRapport valide : {total} signaux, {autres} autres news, {outils} outils, 5 sections.")
    if r.warnings:
        print(f"({len(r.warnings)} avertissement(s) non bloquant(s) ci-dessus — corrige-les si tu peux.)")
    print("Tu peux committer et pousser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
