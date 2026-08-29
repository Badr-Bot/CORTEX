"""
CORTEX — La base de winners de Badr (leçon MASTER RESEARCH · 10 « fichier d'organisation »).

Une seule liste, tenue à jour : chaque pépite du radar quotidien y entre avec
sa date de découverte ; la passe hebdomadaire y ajoute les 10 meilleurs de la
semaine et **rafraîchit** les anciens (pubs actives, courbe, statut : toujours
banger, winner installé, en baisse, mort). Ce qui n'est plus testable sort de
la feuille WINNERS (mais reste dans HISTORIQUE).

Deux colonnes appartiennent à Badr et ne sont JAMAIS écrasées : « Mon verdict »
et « Mes notes ». Un produit qu'il a marqué « écarté » n'est plus reproposé.

Fichiers :
  data/radar/base_winners.json      la vérité (une entrée par boutique)
  data/radar/BASE-WINNERS.xlsx      l'export lisible (WINNERS / HISTORIQUE / LEGENDE)

Commandes :
  python -m agents.base_winners add AAAA-MM-JJ           # pépites du rapport du jour → base
  python -m agents.base_winners refresh AAAA-MM-JJ       # rafraîchit avec le scan du jour (data/radar/AAAA-MM-JJ.json)
  python -m agents.base_winners import-verdicts FICHIER.xlsx   # relit Mon verdict / Mes notes
  python -m agents.base_winners export [FICHIER.xlsx]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("base_winners")

# La base vit sur main. Le workflow de publication (qui tourne sur la branche
# de l'agent) pointe CORTEX_RADAR_DIR vers un checkout de main pour l'y mettre à jour.
RADAR_DIR = Path(os.getenv("CORTEX_RADAR_DIR") or (Path(__file__).parent.parent / "data" / "radar"))
BASE_PATH = RADAR_DIR / "base_winners.json"
XLSX_PATH = RADAR_DIR / "BASE-WINNERS.xlsx"

VERDICTS_BADR = ("", "à tester", "en test", "winner", "écarté", "testé - mort")
STATUTS_VIE = ("BANGER", "EXPLOSE", "SANS TRAFIC", "A SURVEILLER", "STABLE", "EN BAISSE", "MORT")
PRIX_MIN_EUR = 30
MIN_ADS_VIVANT = 50


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def charger() -> dict:
    if BASE_PATH.exists():
        try:
            return json.loads(BASE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.error("base_winners.json illisible — on repart d'une base vide (l'ancien fichier est conservé en .bak)")
            BASE_PATH.replace(BASE_PATH.with_suffix(".bak.json"))
    return {}


def sauver(base: dict) -> None:
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    BASE_PATH.write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")


# ── Règles ───────────────────────────────────────────────────────────────────

def statut_vie(chiffres: dict, precedent: dict | None = None) -> str:
    """Le produit vit-il encore ? MORT = sous le plancher de 50 ads ou courbe
    tombée à moins de la moitié de son pic (04-ecom-data-1.md:271 et :285)."""
    ads = chiffres.get("ads_actives") or 0
    if ads < MIN_ADS_VIVANT:
        return "MORT"
    pic = max([ads] + [h.get("ads", 0) for h in (precedent or {}).get("historique", [])])
    if pic and ads <= pic * 0.5:
        return "MORT"
    accel = chiffres.get("acceleration")
    if accel is not None and accel <= 0.8:
        return "EN BAISSE"
    return chiffres.get("statut") or "STABLE"


def est_testable(entree: dict) -> tuple[bool, str]:
    """Testable = ce que le protocole §1 accepte en testing produit : vivant,
    un marché de Badr ouvert, stade ≤ 3, prix ≥ 30 €, pas d'ingérable, pas
    écarté (par CORTEX ou par Badr)."""
    raisons = []
    if entree.get("verdict_badr") in ("écarté", "testé - mort"):
        raisons.append("écarté par Badr")
    if entree.get("verdict_cortex") == "ECARTER":
        raisons.append("écarté par le radar")
    if entree.get("statut") in ("MORT", "EN BAISSE"):
        raisons.append(f"courbe {entree.get('statut', '').lower()}")
    marches = entree.get("marches") or {}
    if marches and not any(v in ("LIBRE", "PARTIEL") for v in marches.values()):
        raisons.append("aucun marché ouvert")
    stade = entree.get("stade_sophistication")
    if isinstance(stade, int) and stade > 3:
        raisons.append(f"stade {stade} — nouveau mécanisme requis")
    prix = (entree.get("chiffres") or {}).get("prix_eur")
    if prix is not None and prix < PRIX_MIN_EUR:
        raisons.append(f"prix {prix} € sous l'AOV")
    if "INGERABLE" in ((entree.get("chiffres") or {}).get("alertes") or ""):
        raisons.append("ingérable")
    return (not raisons, " + ".join(raisons))


# ── Alimentation ─────────────────────────────────────────────────────────────

def upsert(base: dict, produit: dict, date: str, source: str) -> dict:
    """Ajoute ou met à jour une pépite. Les champs de Badr sont préservés."""
    dom = (produit.get("boutique") or "").lower().replace("https://", "").strip("/")
    if not dom:
        return base
    nouveau = {k: dict(v) for k, v in base.items()}
    ancien = nouveau.get(dom, {})
    chiffres = produit.get("chiffres") or ancien.get("chiffres") or {}
    entree = {
        **ancien,
        "boutique": dom,
        "produit": produit.get("produit") or ancien.get("produit", ""),
        "niche": produit.get("niche") or ancien.get("niche", ""),
        "prix": produit.get("prix") or ancien.get("prix", ""),
        "trouve_le": ancien.get("trouve_le") or date,
        "maj_le": date,
        "source": ancien.get("source") or source,
        "statut": produit.get("statut") or ancien.get("statut", ""),
        "chiffres": chiffres,
        "marches": produit.get("marches") or ancien.get("marches", {}),
        "stade_sophistication": produit.get("stade_sophistication", ancien.get("stade_sophistication")),
        "awareness": produit.get("awareness") or ancien.get("awareness", ""),
        "angle_recommande": produit.get("angle_recommande") or ancien.get("angle_recommande", ""),
        "ou_lancer": produit.get("ou_lancer") or ancien.get("ou_lancer", ""),
        "verdict_cortex": produit.get("verdict") or ancien.get("verdict_cortex", ""),
        "verdict_pourquoi": produit.get("verdict_pourquoi") or ancien.get("verdict_pourquoi", ""),
        "lien_boutique": produit.get("lien_boutique") or ancien.get("lien_boutique") or f"https://{dom}",
        "lien_adlibrary": produit.get("lien_adlibrary") or ancien.get("lien_adlibrary", ""),
        "verdict_badr": ancien.get("verdict_badr", ""),
        "notes_badr": ancien.get("notes_badr", ""),
        "historique": ancien.get("historique", []),
    }
    if chiffres:
        point = {"date": date, "ads": chiffres.get("ads_actives"), "courbe": chiffres.get("courbe_ads"),
                 "statut": entree["statut"]}
        if not entree["historique"] or entree["historique"][-1].get("date") != date:
            entree["historique"] = entree["historique"] + [point]
    ok, raison = est_testable(entree)
    entree["testable"] = ok
    entree["raison_non_testable"] = raison
    nouveau[dom] = entree
    return nouveau


def ajouter_depuis_rapport(base: dict, rapport: dict, date: str) -> dict:
    for p in (rapport.get("ecommerce", {}).get("radar_produits") or []):
        base = upsert(base, p, date, "radar quotidien")
    return base


def rafraichir(base: dict, scan: list[dict], date: str) -> dict:
    """Met à jour les chiffres des produits de la base présents dans un scan."""
    par_dom = {p["boutique"].lower(): p for p in scan}
    nouveau = {k: dict(v) for k, v in base.items()}
    for dom, entree in nouveau.items():
        p = par_dom.get(dom)
        if not p:
            continue
        chiffres = {k: p.get(k) for k in ("ads_actives", "courbe_ads", "acceleration", "delta_ads_7j", "age_jours",
                                           "semaines_diffusion", "visites_mois", "pays_pub", "nb_skus", "prix",
                                           "prix_eur", "alertes", "statut") if k in p}
        statut = statut_vie(chiffres, entree)
        entree.update({"chiffres": {**entree.get("chiffres", {}), **chiffres}, "statut": statut, "maj_le": date})
        entree["historique"] = entree.get("historique", []) + [
            {"date": date, "ads": chiffres.get("ads_actives"), "courbe": chiffres.get("courbe_ads"), "statut": statut}]
        ok, raison = est_testable(entree)
        entree["testable"], entree["raison_non_testable"] = ok, raison
    return nouveau


def testables(base: dict) -> list[dict]:
    rows = [e for e in base.values() if e.get("testable")]
    rows.sort(key=lambda e: (e.get("verdict_cortex") != "GO TEST", -(e.get("chiffres", {}).get("ads_actives") or 0)))
    return rows


# ── Excel ────────────────────────────────────────────────────────────────────

COLONNES = [
    ("trouve_le", "TROUVÉ LE", 11), ("maj_le", "MAJ LE", 11), ("produit", "PRODUIT", 42), ("boutique", "BOUTIQUE", 24),
    ("niche", "NICHE", 16), ("prix", "PRIX VU", 12), ("statut", "STATUT", 13), ("_ads", "PUBS ACTIVES", 10),
    ("_courbe", "COURBE 5 SEM.", 26), ("_accel", "×4 SEM.", 8), ("_age", "ÂGE (j)", 8), ("_pays", "PAYS DE LEURS PUBS", 26),
    ("_marches", "MARCHÉS FR/DE/ES/GB", 30), ("stade_sophistication", "STADE", 7), ("awareness", "AWARENESS", 14),
    ("verdict_cortex", "VERDICT CORTEX", 14), ("ou_lancer", "OÙ LANCER", 40), ("angle_recommande", "ANGLE", 50),
    ("_testable", "TESTABLE ?", 12), ("raison_non_testable", "SINON POURQUOI", 30),
    ("verdict_badr", "MON VERDICT", 14), ("notes_badr", "MES NOTES", 40),
    ("lien_boutique", "BOUTIQUE (lien)", 14), ("lien_adlibrary", "AD LIBRARY", 14),
]


def _valeur(entree: dict, cle: str):
    c = entree.get("chiffres") or {}
    if cle == "_ads": return c.get("ads_actives")
    if cle == "_courbe": return c.get("courbe_ads")
    if cle == "_accel": return c.get("acceleration")
    if cle == "_age": return c.get("age_jours")
    if cle == "_pays": return c.get("pays_pub")
    if cle == "_marches": return " · ".join(f"{k} {v}" for k, v in (entree.get("marches") or {}).items())
    if cle == "_testable": return "OUI" if entree.get("testable") else "non"
    return entree.get(cle, "")


def exporter_xlsx(base: dict, path: Path = XLSX_PATH) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    fills = {"BANGER": "FFFDECEA", "EXPLOSE": "FFEAF5EB", "SANS TRAFIC": "FFF3E5F5", "A SURVEILLER": "FFE9F2FC",
             "STABLE": "FFEDF0F2", "EN BAISSE": "FFFBE9E7", "MORT": "FFEEEEEE"}

    def feuille(nom: str, lignes: list[dict], sous_titre: str):
        ws = wb.create_sheet(nom)
        ws["A1"] = nom
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = sous_titre
        ws["A2"].font = Font(italic=True, size=9, color="FF777777")
        for i, (_, titre, larg) in enumerate(COLONNES, 1):
            c = ws.cell(row=4, column=i, value=titre)
            c.font = Font(bold=True, color="FFFFFFFF", size=9)
            c.fill = PatternFill("solid", fgColor="FF2B2B2B")
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.column_dimensions[get_column_letter(i)].width = larg
        for r, e in enumerate(lignes, 5):
            teinte = fills.get(e.get("statut", ""), "FFFFFFFF")
            for i, (cle, _, _) in enumerate(COLONNES, 1):
                v = _valeur(e, cle)
                c = ws.cell(row=r, column=i, value=v if v not in ("", None) else None)
                c.font = Font(size=9)
                c.fill = PatternFill("solid", fgColor=teinte)
                c.alignment = Alignment(vertical="center", wrap_text=cle in ("angle_recommande", "ou_lancer", "notes_badr", "raison_non_testable"))
                if cle in ("lien_boutique", "lien_adlibrary") and v:
                    c.value = "ouvrir >"
                    c.hyperlink = v
                    c.font = Font(color="FF0563C1", underline="single", size=9)
                if cle in ("verdict_badr", "notes_badr"):
                    c.fill = PatternFill("solid", fgColor="FFFFF8E1")
        ws.freeze_panes = "D5"
        if lignes:
            ws.auto_filter.ref = f"A4:{get_column_letter(len(COLONNES))}{4 + len(lignes)}"

    feuille("WINNERS", testables(base),
            "Uniquement les produits encore testables (vivants, un marché ouvert, stade ≤ 3, prix ≥ 30 €). "
            "MON VERDICT et MES NOTES sont à toi : jamais écrasés. Verdicts possibles : à tester · en test · winner · écarté · testé - mort.")
    tous = sorted(base.values(), key=lambda e: e.get("trouve_le", ""), reverse=True)
    feuille("HISTORIQUE", tous, "Tout ce que le radar a proposé, testable ou non, avec la raison.")
    leg = wb.create_sheet("LEGENDE")
    for i, ligne in enumerate([
        "STATUT : BANGER = trafic 0 + courbe ×2 · EXPLOSE = courbe ×2, trafic visible · SANS TRAFIC = fenêtre ouverte, courbe plate · "
        "A SURVEILLER = 50-149 pubs · STABLE = ≥150 pubs, courbe plate · EN BAISSE = courbe ≤ ×0,8 · MORT = < 50 pubs ou courbe tombée à la moitié du pic",
        "STADE (leçon 33) : 1 = personne · 2 = 1-4 concurrents récents (OK) · 3 = tout le monde dit pareil · 4-5 = saturé",
        "MARCHÉS : LIBRE = personne · PARTIEL = 1-4 récents ou mal exécutés (OK pour lancer) · PRIS = ≥5 ou un acteur dominant · A VERIFIER",
        "TESTABLE : vivant + un marché ouvert + stade ≤ 3 + prix ≥ 30 € + pas d'ingérable + pas écarté (par le radar ou par toi)",
        "Le radar ne repropose jamais un produit marqué « écarté » ou « testé - mort » dans MON VERDICT.",
    ], 1):
        leg.cell(row=i, column=1, value=ligne).alignment = Alignment(wrap_text=True)
    leg.column_dimensions["A"].width = 140
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def importer_verdicts_xlsx(base: dict, path: Path) -> tuple[dict, int]:
    """Relit MON VERDICT / MES NOTES (par nom d'en-tête) dans les deux feuilles."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True)
    nouveau = {k: dict(v) for k, v in base.items()}
    lus = 0
    for nom in ("WINNERS", "HISTORIQUE"):
        if nom not in wb.sheetnames:
            continue
        ws = wb[nom]
        rows = ws.iter_rows(min_row=4, values_only=True)
        entetes = [str(c).strip() if c else "" for c in next(rows, [])]
        if "BOUTIQUE" not in entetes or "MON VERDICT" not in entetes:
            continue
        ib, iv = entetes.index("BOUTIQUE"), entetes.index("MON VERDICT")
        inote = entetes.index("MES NOTES") if "MES NOTES" in entetes else None
        for row in rows:
            dom = str(row[ib] or "").strip().lower()
            if dom not in nouveau:
                continue
            verdict = str(row[iv] or "").strip().lower()
            notes = str(row[inote] or "").strip() if inote is not None else nouveau[dom].get("notes_badr", "")
            if verdict or notes:
                nouveau[dom]["verdict_badr"] = verdict
                nouveau[dom]["notes_badr"] = notes
                ok, raison = est_testable(nouveau[dom])
                nouveau[dom]["testable"], nouveau[dom]["raison_non_testable"] = ok, raison
                lus += 1
    return nouveau, lus


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("date")
    p = sub.add_parser("refresh"); p.add_argument("date")
    p = sub.add_parser("import-verdicts"); p.add_argument("fichier")
    p = sub.add_parser("export"); p.add_argument("fichier", nargs="?", default=str(XLSX_PATH))
    args = parser.parse_args(argv)

    base = charger()
    if args.cmd == "add":
        rapport_path = Path(os.getenv("CORTEX_RAPPORT") or (Path(__file__).parent.parent / "data" / "cowork" / f"rapport_{args.date}.json"))
        if not rapport_path.exists():
            logger.error(f"{rapport_path} introuvable"); return 1
        base = ajouter_depuis_rapport(base, json.loads(rapport_path.read_text(encoding="utf-8")), args.date)
    elif args.cmd == "refresh":
        scan_path = RADAR_DIR / f"{args.date}.json"
        if not scan_path.exists():
            logger.error(f"{scan_path} introuvable"); return 1
        base = rafraichir(base, json.loads(scan_path.read_text(encoding="utf-8")), args.date)
    elif args.cmd == "import-verdicts":
        base, lus = importer_verdicts_xlsx(base, Path(args.fichier))
        logger.info(f"{lus} verdict(s) de Badr relus")
    sauver(base)
    path = exporter_xlsx(base, Path(args.fichier) if args.cmd == "export" else XLSX_PATH)
    logger.info(f"Base : {len(base)} produits, {len(testables(base))} testables → {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
