"""
CORTEX — Validation du rapport rédigé en mode cowork.

Étape 2,5 sur 3 : l'agent Claude lance ce script après avoir écrit son rapport,
et corrige jusqu'à ce qu'il passe au vert. Il vérifie ce qu'un modèle peut rater :

  - structure et valeurs autorisées (le dashboard casse si un champ manque)
  - longueurs minimales (un "fait" de 3 lignes n'explique rien)
  - **URLs réellement présentes dans la collecte du jour** — c'est le garde-fou
    contre la source inventée, la faute la plus grave possible ici

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
RECESSION_KEYS = [
    "courbe_taux", "emploi", "ism_manuf", "ism_services", "conso_conf",
    "credit_spread", "earnings_rev", "pmi_composite", "retail_sales", "housing",
]

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
        value = sig.get(field) or ""
        if isinstance(value, str) and ("**" in value or value.lstrip().startswith("#")):
            r.err(f"{where} : '{field}' contient du markdown — texte brut uniquement")

    url = sig.get("source_url") or ""
    if url and known_urls and url not in known_urls:
        r.err(f"{where} : source_url absente de la collecte du jour — source inventée ? {url}")

    if deeptech:
        if sig.get("horizon") not in DEEPTECH_HORIZONS:
            r.err(f"{where} : horizon deeptech invalide ({sig.get('horizon')!r}) — attendu '5-10' ou '10+'")
        score = sig.get("credibilite_score")
        if not isinstance(score, int) or not 0 <= score <= 4:
            r.err(f"{where} : credibilite_score doit être un entier de 0 à 4")


def check(report: dict, known_urls: set[str]) -> Report:
    r = Report()

    for sector in ("ai", "crypto", "market", "deeptech", "ecommerce"):
        if sector not in report:
            r.err(f"Section '{sector}' absente du rapport")

    # ── IA ────────────────────────────────────────────────────────────────────
    ai = report.get("ai", {})
    signals = ai.get("signals", [])
    if len(signals) != 3:
        r.err(f"ai.signals : 3 signaux attendus, {len(signals)} trouvés")
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"ai.signals[{i}]", known_urls, r)
    if not 2 <= len(ai.get("watchlist", [])) <= 3:
        r.warn(f"ai.watchlist : 2 à 3 items attendus, {len(ai.get('watchlist', []))} trouvés")

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

    signals = crypto.get("signals", [])
    if len(signals) != 3:
        r.err(f"crypto.signals : 3 signaux attendus, {len(signals)} trouvés")
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"crypto.signals[{i}]", known_urls, r)
    if len(crypto.get("trending_alts", [])) != 3:
        r.warn(f"crypto.trending_alts : 3 attendus, {len(crypto.get('trending_alts', []))} trouvés")

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

    signals = market.get("signals", [])
    if len(signals) != 3:
        r.err(f"market.signals : 3 signaux attendus, {len(signals)} trouvés")
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"market.signals[{i}]", known_urls, r)

    # ── DeepTech ──────────────────────────────────────────────────────────────
    signals = report.get("deeptech", {}).get("signals", [])
    if not 2 <= len(signals) <= 3:
        r.err(f"deeptech.signals : 2 à 3 signaux attendus, {len(signals)} trouvés")
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"deeptech.signals[{i}]", known_urls, r, deeptech=True)

    # ── E-commerce ────────────────────────────────────────────────────────────
    ecom = report.get("ecommerce", {})
    if not ecom.get("tendance_globale"):
        r.err("ecommerce.tendance_globale manquante")

    nouveautes = ecom.get("nouveautes", [])
    if not 3 <= len(nouveautes) <= 5:
        r.err(f"ecommerce.nouveautes : 3 à 5 attendues, {len(nouveautes)} trouvées")
    for i, item in enumerate(nouveautes, 1):
        where = f"ecommerce.nouveautes[{i}]"
        if item.get("theme") not in ECOM_THEMES:
            r.err(f"{where} : theme invalide ({item.get('theme')!r}) — attendu {sorted(ECOM_THEMES)}")
        for field in ("titre", "quoi", "pourquoi", "source_url"):
            if not item.get(field):
                r.err(f"{where} : champ '{field}' manquant")
        url = item.get("source_url") or ""
        if url and known_urls and url not in known_urls:
            r.err(f"{where} : source_url absente de la collecte — source inventée ? {url}")

    signals = ecom.get("signals", [])
    if len(signals) != 3:
        r.err(f"ecommerce.signals : 3 signaux attendus, {len(signals)} trouvés")
    themes = []
    for i, sig in enumerate(signals, 1):
        _check_signal(sig, f"ecommerce.signals[{i}]", known_urls, r)
        theme = sig.get("theme")
        if theme not in ECOM_THEMES:
            r.err(f"ecommerce.signals[{i}] : theme invalide ({theme!r})")
        else:
            themes.append(theme)
    if len(set(themes)) < len(themes):
        r.err("ecommerce.signals : les 3 signaux doivent porter sur 3 thèmes DIFFÉRENTS")

    if len(ecom.get("actions_semaine", [])) != 2:
        r.err(f"ecommerce.actions_semaine : 2 attendues, {len(ecom.get('actions_semaine', []))} trouvées")

    return r


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    report_path = COWORK_DIR / f"rapport_{date}.json"
    brief_path = COWORK_DIR / f"collecte_{date}.md"

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
    print(f"\nRapport valide : {total} signaux, 5 sections.")
    if r.warnings:
        print(f"({len(r.warnings)} avertissement(s) non bloquant(s) ci-dessus.)")
    print("Tu peux committer et pousser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
