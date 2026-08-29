"""
CORTEX — Importer les anciens tableaux du Drive de Badr dans la base de winners.

Badr avait deux tableaux Google Sheets dans « 05 — RECHERCHE PRODUITS » :
  - RADAR TOP        : le scan large (une ligne par boutique, chiffres bruts)
  - PRODUCT RADAR    : l'analyse approfondie (marchés, où lancer, commentaire)
Tout doit finir au même endroit : la base Notion. Ce module lit les CSV
exportés et les convertit au format de `base_winners`, sans jamais écraser un
produit déjà présent ni un verdict de Badr.

  python -m agents.import_drive data/radar/drive_radar_top.csv data/radar/drive_product_radar.csv
"""

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

from agents.base_winners import charger, sauver, est_testable, statut_vie
from utils.logger import get_logger

logger = get_logger("import_drive")

SOURCE = "tableaux Drive (import)"
TAUX_EUR = {"USD": 0.92, "EUR": 1.0, "GBP": 1.17, "AUD": 0.60, "SEK": 0.088,
            "NOK": 0.086, "DKK": 0.134, "CHF": 1.05, "CAD": 0.68}


def _norm(s: str) -> str:
    """En-tête → clé comparable : sans accents, sans emoji, minuscules."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _col(ligne: dict, *candidats: str) -> str:
    """Valeur d'une colonne repérée par un morceau de son intitulé."""
    for cand in candidats:
        c = _norm(cand)
        for cle, val in ligne.items():
            n = _norm(cle)
            if n == c or (c and c in n):
                v = str(val or "").strip()
                if v:
                    return v
    return ""


def _nombre(txt: str):
    m = re.search(r"-?\d[\d\s ]*(?:[.,]\d+)?", str(txt or "").replace(" ", " "))
    if not m:
        return None
    try:
        return float(m.group(0).replace(" ", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _prix_eur(txt: str):
    """« 59.9 USD » → 55.1 ; « 399 SEK » → 35.1 (règle prix ≥ 30 € de la formation)."""
    val = _nombre(txt)
    if val is None:
        return None
    devise = next((d for d in TAUX_EUR if d in str(txt).upper()), "EUR")
    return round(val * TAUX_EUR[devise], 2)


def _domaine(txt: str) -> str:
    """Domaine, avec le chemin produit s'il y en a un : une même boutique peut
    pousser deux produits différents (WildNest = GroundGuard ET CloudNest)."""
    d = re.sub(r"^https?://", "", str(txt or "").strip().lower()).rstrip("/")
    if "/products/" in d:
        return d
    return d.split("/")[0].strip()


def _marche(txt: str) -> str:
    """« PRIS - Callie France… » → PRIS ; « a verifier » → A VERIFIER."""
    t = _norm(txt)
    if not t:
        return "A VERIFIER"
    if "sans objet" in t:
        return "A VERIFIER"
    for mot, val in (("libre", "LIBRE"), ("partiel", "PARTIEL"), ("pris", "PRIS")):
        if t.startswith(mot) or f" {mot}" in f" {t}":
            return val
    return "A VERIFIER"


def _statut(txt: str) -> str:
    t = _norm(txt)
    for mot, val in (("banger", "BANGER"), ("explose", "EXPLOSE"), ("scale", "EXPLOSE"),
                     ("sans trafic", "SANS TRAFIC"), ("surveiller", "A SURVEILLER"),
                     ("baisse", "EN BAISSE"), ("mort", "MORT")):
        if mot in t:
            return val
    return "STABLE"


def _verdict(txt: str) -> str:
    t = _norm(txt)
    if "fonce" in t or "go test" in t or "priorite" in t:
        return "GO TEST"
    if "trop tard" in t or "ecarte" in t or "rien en l etat" in t or "pas la france" in t:
        return "ECARTER"
    return "A SURVEILLER"


def _verdict_badr(txt: str) -> str:
    t = _norm(txt)
    for mot, val in (("winner", "testé - winner"), ("mort", "testé - mort"), ("ecarte", "écarté"),
                     ("en test", "en test"), ("tester", "à tester")):
        if mot in t:
            return val
    return ""


def ligne_vers_produit(ligne: dict, date: str) -> dict | None:
    """Une ligne de CSV → une entrée de base (format `upsert`)."""
    dom = _domaine(_col(ligne, "boutique", "lien boutique"))
    produit = _col(ligne, "produit")
    if not dom or not produit or _norm(produit) in ("", "produit"):
        return None
    prix = _col(ligne, "prix vu", "prix")
    ads = _nombre(_col(ligne, "ads actives", "ads"))
    chiffres = {k: v for k, v in {
        "ads_actives": int(ads) if ads is not None else None,
        "courbe_ads": _col(ligne, "courbe"),
        "acceleration": _nombre(_col(ligne, "x4 sem", "x4 semaines")),
        "age_jours": int(_nombre(_col(ligne, "age j", "age")) or 0) or None,
        "visites_mois": _nombre(_col(ligne, "trafic mois", "trafic")),
        "pays_pub": _col(ligne, "pays de leurs pubs", "marches actifs"),
        "nb_skus": int(_nombre(_col(ligne, "sku")) or 0) or None,
        "prix": prix,
        "prix_eur": _prix_eur(prix),
        "statut": _statut(_col(ligne, "statut")),   # statut_vie le respecte si la boutique est vivante
    }.items() if v not in (None, "")}

    fr = _marche(_col(ligne, "marche fr", "france"))
    marches = {"FR": fr, "DE": "A VERIFIER", "ES": "A VERIFIER", "GB": "A VERIFIER"}
    libres = _col(ligne, "marches libres")
    # « DE et ES a verifier » ne veut pas dire libre. En revanche « DE, ES, IT
    # (verifie le 24/08) » veut bien dire libre : c'est un contrôle déjà fait.
    if libres and "a verifier" not in _norm(libres):
        for pays in ("DE", "ES", "GB"):
            if re.search(rf"\b{pays}\b", libres, re.I):
                marches[pays] = "LIBRE"

    commentaire = _col(ligne, "commentaire formation", "le verdict", "commentaire")
    # Règle de Badr : rien d'ingérable. Le tableau le disait en toutes lettres.
    contexte = _norm(f"{produit} {_col(ligne, 'niche')} {commentaire} {_col(ligne, 'france')}")
    if any(mot in contexte for mot in ("ingerable", "complement", "supplement", "extract", "cleanse", "drops",
                                       "capsules", "gelules", "sante complements")):
        chiffres["alertes"] = "INGERABLE — complément alimentaire, écarté par ta règle"
    detail = {}
    for source_col, pays in (("marche fr", "FR"), ("france", "FR")):
        txt = _col(ligne, source_col)
        if txt and len(txt) > 12:
            detail["FR"] = txt
            break
    if libres:
        detail["Marchés libres relevés à l'époque"] = libres

    return {
        "boutique": dom,
        "produit": produit,
        "niche": _col(ligne, "niche"),
        "prix": prix,
        "statut": _statut(_col(ligne, "statut")),
        "chiffres": chiffres,
        "marches": marches,
        "marches_detail": detail,
        "ou_lancer": _col(ligne, "ou lancer"),
        "verdict": _verdict(commentaire or _col(ligne, "le verdict")),
        "verdict_pourquoi": commentaire,
        "tam": _col(ligne, "reach 30j") and f"Reach 30 jours relevé à l'époque : {_col(ligne, 'reach 30j')}" or "",
        "lien_boutique": _col(ligne, "lien boutique") or f"https://{dom}",
        "lien_adlibrary": _col(ligne, "lien ad library", "ad library"),
        "_verdict_badr": _verdict_badr(_col(ligne, "verdict badr", "ton verdict")),
        "_notes_badr": _col(ligne, "notes badr", "tes notes"),
        "_score": _nombre(_col(ligne, "score")),
        "_a_verifier": _col(ligne, "a verifier"),
    }


def importer(base: dict, chemins: list[Path], date: str) -> tuple[dict, int, int]:
    """Ajoute les produits des CSV. Un produit déjà dans la base n'est jamais dégradé."""
    from agents.base_winners import upsert

    ajoutes = ignores = 0
    for chemin in chemins:
        with chemin.open(encoding="utf-8-sig", newline="") as f:
            for ligne in csv.DictReader(f):
                p = ligne_vers_produit(ligne, date)
                if not p:
                    ignores += 1
                    continue
                dom = p["boutique"]
                deja = dom in base
                base = upsert(base, p, date, SOURCE)
                e = base[dom]
                if not deja:
                    e["trouve_le"] = date          # date du tableau, pas d'aujourd'hui
                    ajoutes += 1
                # les colonnes de Badr, seulement si elles étaient remplies dans son tableau
                if p["_verdict_badr"] and not e.get("verdict_badr"):
                    e["verdict_badr"] = p["_verdict_badr"]
                if p["_notes_badr"] and not e.get("notes_badr"):
                    e["notes_badr"] = p["_notes_badr"]
                if p["_score"] and not e.get("criteres_ok"):
                    e["criteres_ok"] = [f"{int(p['_score'])} critères cochés dans ton tableau du Drive"] * int(p["_score"])
                if p["_a_verifier"] and not e.get("raison_non_testable"):
                    e.setdefault("a_verifier", p["_a_verifier"])
                e["statut"] = statut_vie(e.get("chiffres") or {}, e)
                ok, raison = est_testable(e)
                e["testable"], e["raison_non_testable"] = ok, raison
    return base, ajoutes, ignores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--date", default="", help="date de découverte (défaut : celle du nom de fichier)")
    args = parser.parse_args(argv)

    base = charger()
    avant = len(base)
    for chemin in args.csv:
        p = Path(chemin)
        if not p.exists():
            logger.error(f"{p} introuvable")
            return 1
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        date = args.date or (m.group(1) if m else "2026-08-26")
        base, ajoutes, ignores = importer(base, [p], date)
        logger.info(f"{p.name} : {ajoutes} produit(s) ajouté(s), {ignores} ligne(s) ignorée(s)")
    sauver(base)
    from agents.base_winners import testables
    logger.info(f"Base : {avant} → {len(base)} produits, {len(testables(base))} testables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
