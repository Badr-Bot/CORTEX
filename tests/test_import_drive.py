"""Import des anciens tableaux Drive de Badr dans la base de winners."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.import_drive import ligne_vers_produit, importer, _marche, _prix_eur, _statut, _verdict_badr  # noqa: E402

LIGNE_TOP = {
    "#": "26", "STATUT": "🔴 BANGER", "MARCHE FR": "⬜ a verifier", "VRAIE BRAND ?": "⬜ non",
    "PRODUIT": "Banish 14+ Pests for Good", "BOUTIQUE": "pestprohome.com",
    "PAYS DE LEURS PUBS (%)": "GB 36%, CA 19%, US 17%", "x4 SEM.": "4.3", "ADS": "139",
    "COURBE 5 SEMAINES": "25 > 108", "PRIX": "59.9 USD", "SKU": "3", "MARGE x3-x4 ?": "a calculer",
    "A VERIFIER": "", "LE VERDICT": "🔵 A CREUSER. x4.3 en 4 sem., 139 ads, 2 sem. de diffusion.",
    "TON VERDICT": "", "TES NOTES": "", "LIEN": "https://pestprohome.com",
}
LIGNE_ANALYSE = {
    "RANG": "6", "PRODUIT": "GroundGuard (chaussettes de travail)", "BOUTIQUE": "getwildnest.com",
    "NICHE": "Outils & métiers", "STATUT": "BANGER", "SCORE /9": "8/9", "ADS ACTIVES": "616",
    "AGE (j)": "24", "REACH 30j": "1943261", "TRAFIC/MOIS brut (x5-x10)": "0",
    "MARCHES ACTIFS": "GB, NZ, AU, CA, US (Big Five)",
    "FRANCE ?": "PRIS - Solina (solina-official.com), ~10 ads actives, 270 creees, depuis le 15/08",
    "MARCHES LIBRES": "DE, ES, IT, AT, CH, BE (verifie le 24/08)",
    "OU LANCER (reco)": "DE en priorite 1 : marche libre au 24/08, plus gros effectif BTP d'Europe.",
    "PRIX VU": "25,99 USD", "COMMENTAIRE FORMATION (Matteo)": "MASTER RESEARCH . 3 : boutique a 0 visiteur + des centaines d'ads actives.",
    "VERDICT BADR": "", "NOTES BADR": "", "LIEN BOUTIQUE": "https://getwildnest.com/products/groundguard",
    "LIEN AD LIBRARY": "https://www.facebook.com/ads/library/?q=groundguard",
}


def test_lecture_d_une_ligne_du_scan_large():
    p = ligne_vers_produit(LIGNE_TOP, "2026-08-26")
    assert p["boutique"] == "pestprohome.com" and p["statut"] == "BANGER"
    assert p["chiffres"]["ads_actives"] == 139 and p["chiffres"]["acceleration"] == 4.3
    assert p["chiffres"]["courbe_ads"] == "25 > 108" and p["chiffres"]["nb_skus"] == 3
    assert p["chiffres"]["prix_eur"] == round(59.9 * 0.92, 2)   # ≥ 30 € : passe le filtre
    assert p["marches"]["FR"] == "A VERIFIER"


def test_lecture_d_une_ligne_de_l_analyse_approfondie():
    p = ligne_vers_produit(LIGNE_ANALYSE, "2026-08-25")
    assert p["boutique"] == "getwildnest.com" and p["niche"] == "Outils & métiers"
    assert p["marches"]["FR"] == "PRIS"
    assert p["marches"]["DE"] == "LIBRE" and p["marches"]["ES"] == "LIBRE"
    assert p["chiffres"]["age_jours"] == 24 and p["chiffres"]["ads_actives"] == 616
    assert "Solina" in p["marches_detail"]["FR"]
    assert p["ou_lancer"].startswith("DE en priorite")
    assert p["_score"] == 8


def test_un_marche_a_verifier_n_est_pas_marque_libre():
    # « DE et ES a verifier » (holdmategear) : rien n'est libre…
    a_verifier = dict(LIGNE_ANALYSE, **{"MARCHES LIBRES": "DE et ES a verifier - FR est hors jeu"})
    assert ligne_vers_produit(a_verifier, "2026-08-25")["marches"]["DE"] == "A VERIFIER"
    # … alors que « DE, ES, IT (verifie le 24/08) » est un contrôle déjà fait.
    assert ligne_vers_produit(LIGNE_ANALYSE, "2026-08-25")["marches"]["DE"] == "LIBRE"


def test_les_lignes_sans_produit_sont_ignorees():
    assert ligne_vers_produit({"PRODUIT": "", "BOUTIQUE": ""}, "2026-08-26") is None
    assert ligne_vers_produit({"PRODUIT": "Produit d'insecte été", "BOUTIQUE": ""}, "2026-08-26") is None


def test_import_n_ecrase_pas_le_verdict_de_badr(tmp_path):
    base = {"pestprohome.com": {"boutique": "pestprohome.com", "produit": "PestPro", "verdict_badr": "écarté",
                                "notes_badr": "déjà vu", "trouve_le": "2026-08-20", "chiffres": {"ads_actives": 170}}}
    csv_path = tmp_path / "t.csv"
    import csv as _csv
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(LIGNE_TOP))
        w.writeheader(); w.writerow(LIGNE_TOP)
    base, ajoutes, _ = importer(base, [csv_path], "2026-08-26")
    e = base["pestprohome.com"]
    assert ajoutes == 0                       # déjà connu
    assert e["verdict_badr"] == "écarté" and e["notes_badr"] == "déjà vu"
    assert e["trouve_le"] == "2026-08-20"     # la date d'origine est gardée
    assert e["testable"] is False and "Badr" in e["raison_non_testable"]


def test_un_vieux_tableau_n_ecrase_pas_une_analyse_plus_recente(tmp_path):
    """Le scan du 26/08 ne doit pas rendre à « a verifier » un marché contrôlé le 29/08."""
    base = {"pestprohome.com": {"boutique": "pestprohome.com", "produit": "PestPro", "trouve_le": "2026-08-29",
                                "maj_le": "2026-08-29", "marches": {"FR": "PARTIEL", "DE": "PRIS"},
                                "marches_detail": {"FR": "81 pubs, Nuizoff 16 pubs depuis 10 j"},
                                "verdict_cortex": "GO TEST", "stade_sophistication": 2,
                                "chiffres": {"ads_actives": 170, "acceleration": 5.1, "prix_eur": 41.4}}}
    csv_path = tmp_path / "vieux.csv"
    import csv as _csv
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(LIGNE_TOP))
        w.writeheader(); w.writerow(LIGNE_TOP)          # même boutique, données du 26/08
    base, _, _ = importer(base, [csv_path], "2026-08-26")
    e = base["pestprohome.com"]
    assert e["marches"]["FR"] == "PARTIEL" and e["marches"]["DE"] == "PRIS"
    assert "Nuizoff" in e["marches_detail"]["FR"]
    assert e["verdict_cortex"] == "GO TEST" and e["chiffres"]["ads_actives"] == 170
    assert e["maj_le"] == "2026-08-29"
    assert e["testable"] is True


def test_conversions():
    assert _marche("PARTIEL - la mousseline est travaillee en FR") == "PARTIEL"
    assert _marche("SANS OBJET - complement non lance en France") == "A VERIFIER"
    assert _marche("") == "A VERIFIER"
    assert _prix_eur("399 SEK") == round(399 * 0.088, 2)
    assert _statut("🟢 EXPLOSE") == "EXPLOSE" and _statut("EN TRAIN DE SCALE") == "EXPLOSE"
    assert _verdict_badr("teste - winner") == "testé - winner" and _verdict_badr("") == ""
