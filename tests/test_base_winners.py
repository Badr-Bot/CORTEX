"""Tests de la base de winners — la règle d'or : les verdicts de Badr ne sont jamais écrasés."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.base_winners import upsert, est_testable, statut_vie, rafraichir, exporter_xlsx, importer_verdicts_xlsx
from agents.base_winners import testables as produits_testables  # renommé : pytest prendrait « testables » pour un test


def _pepite(**extra):
    p = {"produit": "PestPro", "boutique": "pestprohome.com", "niche": "Maison", "prix": "45 USD", "statut": "BANGER",
         "marches": {"FR": "PARTIEL", "DE": "PARTIEL"}, "stade_sophistication": 2, "verdict": "GO TEST",
         "chiffres": {"ads_actives": 170, "courbe_ads": "25 > 128", "acceleration": 5.1, "prix_eur": 41.4},
         "lien_boutique": "https://pestprohome.com"}
    p.update(extra)
    return p


def test_ajout_et_date_de_decouverte_conservee():
    base = upsert({}, _pepite(), "2026-08-29", "radar quotidien")
    base = upsert(base, _pepite(chiffres={"ads_actives": 300, "courbe_ads": "25 > 128 > 300", "acceleration": 6}), "2026-09-05", "passe hebdo")
    e = base["pestprohome.com"]
    assert e["trouve_le"] == "2026-08-29" and e["maj_le"] == "2026-09-05"
    assert [h["ads"] for h in e["historique"]] == [170, 300]
    assert e["testable"]


def test_verdict_badr_jamais_ecrase():
    base = upsert({}, _pepite(), "2026-08-29", "radar quotidien")
    base["pestprohome.com"]["verdict_badr"] = "écarté"
    base["pestprohome.com"]["notes_badr"] = "pas pour moi"
    base = upsert(base, _pepite(), "2026-09-05", "passe hebdo")
    e = base["pestprohome.com"]
    assert e["verdict_badr"] == "écarté" and e["notes_badr"] == "pas pour moi"
    assert not e["testable"] and "écarté par Badr" in e["raison_non_testable"]


def test_testable_refuse_les_marches_fermes_et_le_stade_4():
    assert est_testable({"marches": {"FR": "PRIS", "DE": "PRIS"}})[0] is False
    ok, raison = est_testable({"marches": {"FR": "LIBRE"}, "stade_sophistication": 4})
    assert not ok and "stade 4" in raison
    assert est_testable({"marches": {"FR": "LIBRE"}, "stade_sophistication": 2, "chiffres": {"prix_eur": 45}})[0]


def test_statut_vie_mort_sous_50_ads_ou_moitie_du_pic():
    assert statut_vie({"ads_actives": 30}) == "MORT"
    assert statut_vie({"ads_actives": 200, "statut": "BANGER"}, {"historique": [{"ads": 600}]}) == "MORT"
    assert statut_vie({"ads_actives": 200, "acceleration": 0.7}, {"historique": [{"ads": 220}]}) == "EN BAISSE"
    assert statut_vie({"ads_actives": 200, "acceleration": 1.5, "statut": "EXPLOSE"}, {"historique": [{"ads": 150}]}) == "EXPLOSE"


def test_refresh_sort_un_produit_mort_de_la_liste_testable():
    base = upsert({}, _pepite(), "2026-08-29", "radar quotidien")
    scan = [{"boutique": "pestprohome.com", "ads_actives": 20, "courbe_ads": "25 > 128 > 20", "acceleration": 0.2, "statut": "SOUS LE FILTRE"}]
    base = rafraichir(base, scan, "2026-09-05")
    e = base["pestprohome.com"]
    assert e["statut"] == "MORT" and not e["testable"] and len(e["historique"]) == 2
    assert produits_testables(base) == []


def test_export_et_relecture_des_verdicts(tmp_path):
    base = upsert({}, _pepite(), "2026-08-29", "radar quotidien")
    path = exporter_xlsx(base, tmp_path / "base.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(path)
    ws = wb["WINNERS"]
    entetes = [c.value for c in ws[4]]
    ws.cell(row=5, column=entetes.index("MON VERDICT") + 1, value="à tester")
    ws.cell(row=5, column=entetes.index("MES NOTES") + 1, value="tester en pack de 2")
    wb.save(path)
    base2, lus = importer_verdicts_xlsx(base, path)
    assert lus == 1
    assert base2["pestprohome.com"]["verdict_badr"] == "à tester"
    assert base2["pestprohome.com"]["notes_badr"] == "tester en pack de 2"
