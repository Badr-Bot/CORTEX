"""
Tests du radar produits — sans réseau : le classement des boutiques, la fusion
des domaines miroirs et le choix des candidats. Un mauvais statut enverrait à
Badr un produit en baisse comme une pépite.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from agents.radar_produits import (
    classify, fusionner_reseaux, build_day, candidats, update_suivi, mark_analysed,
    _looks_like_search_shops,
)

TODAY = date(2026, 8, 29)


def _row(domain="shop.com", ads=300, history=(50, 60, 120, 250, 300), visits=0,
         created="2026-07-20", title="Lampe de bureau pliable", price=39.9,
         currency="USD", products=3, countries=None):
    return {
        "domain": domain, "name": domain.split(".")[0], "createdAt": created + "T00:00:00Z",
        "profile": {"countryCode": "US", "currency": currency},
        "catalog": {"productsCount": products, "mainCategory": "Home",
                    "bestSellers": [{"title": title, "price": price, "currency": currency}]},
        "traffic": {"monthlyVisits": visits, "history": []},
        "advertising": {"activeAds": ads,
                        "history": [{"period": f"2026-0{i+3}-01", "value": v} for i, v in enumerate(history)],
                        "topCountries": countries or []},
    }


def test_banger_quand_trafic_zero_et_courbe_explose():
    p = classify(_row(), techno=False, today=TODAY)
    assert p["statut"] == "BANGER"
    assert p["acceleration"] == 6.0
    assert p["invisible"] is True


def test_sans_trafic_quand_courbe_plate():
    p = classify(_row(history=(200, 210, 205, 215, 220)), False, TODAY)
    assert p["statut"] == "SANS TRAFIC"


def test_explose_quand_trafic_visible():
    p = classify(_row(visits=12000), False, TODAY)
    assert p["statut"] == "EXPLOSE"


def test_en_baisse_est_un_anti_signal():
    p = classify(_row(history=(500, 400, 300, 200, 150), visits=5000), False, TODAY)
    assert p["statut"] == "EN BAISSE"


def test_sous_le_filtre_sous_50_ads():
    p = classify(_row(ads=30), False, TODAY)
    assert p["statut"] == "SOUS LE FILTRE"


def test_ingerable_signale_et_penalise():
    p = classify(_row(title="Collagen Powder Vanilla"), False, TODAY)
    assert "INGERABLE" in p["alertes"]
    q = classify(_row(), False, TODAY)
    assert p["priorite"] < q["priorite"]


def test_titre_upsell_ignore_au_profit_du_vrai_produit():
    row = _row()
    row["catalog"]["bestSellers"] = [
        {"title": "VIP Membership", "price": 4.99, "currency": "USD"},
        {"title": "Lampe de bureau pliable", "price": 39.9, "currency": "USD"},
    ]
    assert classify(row, False, TODAY)["produit"] == "Lampe de bureau pliable"


def test_france_ciblee_et_marches_libres():
    p = classify(_row(countries=[{"countryCode": "US", "share": 0.6}, {"countryCode": "FR", "share": 0.4}]), False, TODAY)
    assert p["fr_dans_leurs_pubs"].startswith("OUI")
    assert "FR" not in p["marches_libres"] and "DE" in p["marches_libres"]


def test_pays_non_indexes_ne_concluent_jamais_libre():
    p = classify(_row(countries=[]), False, TODAY)
    assert p["marches_libres"] == "inconnu"


def test_fusion_des_domaines_miroirs():
    a = classify(_row("a.com", created="2026-07-01"), False, TODAY)
    b = classify(_row("b.com", created="2026-08-10"), False, TODAY)
    c = classify(_row("c.com", history=(10, 20, 30, 40, 55)), False, TODAY)
    garde = fusionner_reseaux([a, b, c])
    domaines = {p["boutique"] for p in garde}
    assert domaines == {"b.com", "c.com"}, "le domaine le plus récent représente le réseau"
    assert "a.com" in next(p for p in garde if p["boutique"] == "b.com")["reseau"]


def test_build_day_trie_et_numerote():
    payload = {"data": [_row("x.com"), _row("y.com", ads=30)], "raw": {"request": {"parsedArgs": {}}}}
    day = build_day([(payload, False)], TODAY)
    assert [p["rang"] for p in day] == [1, 2]
    assert day[0]["boutique"] == "x.com"


def test_candidats_excluent_analyses_recentes_et_ingerables():
    us = [{"countryCode": "US", "share": 1.0}]
    payload = {"data": [_row("fresh.com", countries=us), _row("done.com", countries=us),
                        _row("gummy.com", title="Sleep Gummies", countries=us)],
               "raw": {}}
    day = build_day([(payload, False)], TODAY)
    suivi = update_suivi({}, day, "2026-08-29")
    suivi = mark_analysed(suivi, "2026-08-27", ["done.com"])
    noms = [p["boutique"] for p in candidats(day, suivi, "2026-08-29")]
    assert "fresh.com" in noms and "done.com" not in noms and "gummy.com" not in noms


def test_regles_de_qualification_de_badr():
    """Feuille WINNERS du 26/08 : prix bas, France déjà ciblée, hors Big Five,
    pays non indexés, catalogue généraliste et ingérables sont écartés."""
    from agents.radar_produits import qualifie
    ok, _ = qualifie(classify(_row(countries=[{"countryCode": "US", "share": 1.0}]), False, TODAY))
    assert ok
    cas = {
        "prix bas": _row(price=19.99, countries=[{"countryCode": "US", "share": 1.0}]),
        "cible déjà la France": _row(countries=[{"countryCode": "FR", "share": 0.5}, {"countryCode": "US", "share": 0.5}]),
        "hors Big Five": _row(currency="KWD", countries=[{"countryCode": "US", "share": 1.0}]),
        "non indexés": _row(countries=[]),
        "catalogue": _row(products=45, countries=[{"countryCode": "US", "share": 1.0}]),
        "ingérable": _row(title="Magnesium Gummies", countries=[{"countryCode": "US", "share": 1.0}]),
    }
    for attendu, row in cas.items():
        ok, raison = qualifie(classify(row, False, TODAY))
        assert not ok and attendu in raison, (attendu, raison)


def test_candidats_appliquent_les_regles_de_badr():
    payload = {"data": [
        _row("ok.com", countries=[{"countryCode": "US", "share": 1.0}]),
        _row("cheap.com", price=12.0, countries=[{"countryCode": "US", "share": 1.0}]),
        _row("fr.com", countries=[{"countryCode": "FR", "share": 0.9}]),
    ], "raw": {}}
    day = build_day([(payload, False)], TODAY)
    noms = [p["boutique"] for p in candidats(day, {}, "2026-08-29")]
    assert noms == ["ok.com"]


def test_suivi_conserve_les_analyses_et_les_rangs():
    day = build_day([({"data": [_row("s.com")]}, False)], TODAY)
    suivi = update_suivi({"s.com": {"premiere_vue": "2026-08-20", "analyse_le": ["2026-08-20"], "rangs": {"2026-08-20": 9}}},
                         day, "2026-08-29")
    assert suivi["s.com"]["analyse_le"] == ["2026-08-20"]
    assert suivi["s.com"]["rangs"] == {"2026-08-20": 9, "2026-08-29": 1}
    assert suivi["s.com"]["premiere_vue"] == "2026-08-20"


def test_detection_du_format_search_shops():
    assert _looks_like_search_shops({"data": [{"domain": "a.com"}]})
    assert not _looks_like_search_shops({"data": []})
    assert not _looks_like_search_shops({"hits": [{"domain": "a.com"}]})
