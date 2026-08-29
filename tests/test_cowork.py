"""
Tests du mode cowork — le rapport rédigé par un agent Claude planifié.

Chaîne testée : collecte (aucun modèle) → rédaction (l'agent) → validation →
publication. Ces tests portent sur la validation et la publication, les deux
endroits où une erreur de l'agent pourrait casser le rapport ou, pire, faire
passer une source inventée pour une vraie.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import copy

import pytest

from cowork_check import check

URL_A = "https://exemple.fr/article-a"
URL_B = "https://exemple.fr/article-b"
URL_C = "https://exemple.fr/article-c"
KNOWN_URLS = {URL_A, URL_B, URL_C}

LONG = (
    "Explication complète et pédagogique de ce qui s'est passé, avec le contexte "
    "nécessaire pour comprendre sans être expert du sujet. On y trouve les chiffres "
    "clés, qui sont les acteurs concernés, et pourquoi cela arrive maintenant plutôt "
    "qu'il y a six mois. Chaque terme technique est expliqué entre parenthèses dès "
    "sa première apparition, de façon que la lecture reste fluide pour quelqu'un qui "
    "découvre le sujet. On termine en reliant ce fait à la situation générale du "
    "secteur, pour que le lecteur sache où ranger cette information dans sa tête."
)
MID = (
    "Conséquence directe expliquée simplement, avec ce que cela change concrètement "
    "pour une décision à prendre dans les prochaines semaines, et sur quel montant."
)


def _signal(url=URL_A, **extra):
    sig = {
        "conviction": 4,
        "title": "UN TITRE FACTUEL EN MAJUSCULES",
        "en_clair": "Une phrase simple qui résume l'essentiel sans aucun jargon technique.",
        "fait": LONG,
        "implication_2": MID,
        "implication_3": MID,
        "these_opposee": "Le meilleur argument contre cette lecture, formulé honnêtement et avec des faits.",
        "action": "Action concrète et précise à mener, avec un délai et un seuil clairs.",
        "sizing": "Moyen",
        "invalide_si": "Le seuil précis et mesurable qui invaliderait cette analyse.",
        "source_name": "Source",
        "source_url": url,
    }
    sig.update(extra)
    return sig


def _deeptech_signal(url=URL_A):
    return _signal(url, horizon="5-10", credibilite_score=3, peer_reviewed=True,
                   peer_reviewed_detail="Nature, 2026", financement=False, financement_detail="",
                   prototype=True, prototype_detail="Démonstration publique", adoption=False,
                   adoption_detail="", investissement_cotes=["NVDA"], investissement_etf=[],
                   investissement_early=[])


def _autres_news(n: int = 4) -> list[dict]:
    return [
        {"titre": f"News {i}", "en_clair": "Ce qui s'est passé et pourquoi ça compte, en une phrase simple.",
         "source_name": "Source", "source_url": URL_B}
        for i in range(n)
    ]


def _outil(url=URL_A, categorie="video") -> dict:
    return {
        "nom": "Outil", "categorie": categorie, "quoi": "Ce que fait l'outil.",
        "pour_toi": "Ce que Badr en ferait.", "comment_tester": "Cloner et lancer.",
        "gratuit": True, "source_name": "GitHub", "source_url": url,
    }


@pytest.fixture
def rapport():
    return {
        "ai": {
            "signals": [_signal(URL_A), _signal(URL_B), _signal(URL_C)],
            "watchlist": ["Premier signal à surveiller", "Deuxième signal à confirmer"],
            "trending_repos": [
                {"nom": "org/repo", "type": "repo", "quoi": "Un outil.", "pour_toi": "Utile pour X.",
                 "popularite": "1 000 étoiles", "source_url": URL_C}
            ] * 3,
            "autres_news": _autres_news(),
        },
        "crypto": {
            "phase": "Accumulation",
            "recommandation": {"verdict": "ACCUMULER", "alts": "ATTENDRE",
                               "horizon": "2-4 semaines", "raisonnement": "Justification chiffrée."},
            "trending_alts": [{"ticker": "SOL", "nom": "Solana", "theme": "t",
                               "signal": "s", "verdict": "SURVEILLER", "timing": "x"}] * 3,
            "volume_vs_30d": "Volume en dessous de la moyenne du mois.",
            "score": {k: {"value": 0, "note": "Justification avec des données concrètes."}
                      for k in ("onchain", "cycle", "macro", "sentiment", "momentum")},
            "direction": "NEUTRE",
            "magnitude": "faible",
            "bear_case": "Ce qui invaliderait cette lecture, avec des seuils précis.",
            "signals": [_signal(URL_A), _signal(URL_B), _signal(URL_C)],
            "autres_news": _autres_news(),
        },
        "market": {
            "recession_indicators": {
                k: {"status": "yellow", "note": "Note chiffrée expliquant l'état de l'indicateur."}
                for k in ("courbe_taux", "emploi", "ism_manuf", "ism_services", "conso_conf",
                          "credit_spread", "earnings_rev", "pmi_composite", "retail_sales", "housing")
            },
            "recession_score": 3,
            "regime": "Transition",
            "regime_justification": "Le régime actuel expliqué simplement en plusieurs lignes.",
            "signals": [_signal(URL_A), _signal(URL_B), _signal(URL_C)],
            "autres_news": _autres_news(),
        },
        "deeptech": {"signals": [_deeptech_signal(URL_A), _deeptech_signal(URL_B)],
                     "autres_news": _autres_news()},
        "ecommerce": {
            "tendance_globale": "Ce qui bouge en e-commerce en ce moment, expliqué simplement.",
            "outils": [_outil(URL_A, "video"), _outil(URL_B, "produit_gagnant"), _outil(URL_C, "pub")],
            "radar_produits": [],
            "autres_news": _autres_news(),
            "nouveautes": [
                {"theme": "automation", "titre": "T1", "quoi": "Q1", "pourquoi": "P1",
                 "source_name": "S", "source_url": URL_A},
                {"theme": "emailing", "titre": "T2", "quoi": "Q2", "pourquoi": "P2",
                 "source_name": "S", "source_url": URL_B},
                {"theme": "creatives", "titre": "T3", "quoi": "Q3", "pourquoi": "P3",
                 "source_name": "S", "source_url": URL_C},
            ],
            "signals": [
                _signal(URL_A, theme="automation"),
                _signal(URL_B, theme="emailing"),
                _signal(URL_C, theme="creatives"),
            ],
            "actions_semaine": ["Première action testable", "Deuxième action testable"],
        },
    }


# ── Le cas nominal ────────────────────────────────────────────────────────────

def test_rapport_complet_est_valide(rapport):
    r = check(rapport, KNOWN_URLS)
    assert not r.errors, f"Rapport correct rejeté : {r.errors}"


# ── Le garde-fou principal : pas de source inventée ───────────────────────────

def test_url_inventee_est_refusee(rapport):
    rapport["ai"]["signals"][0]["source_url"] = "https://source-inventee.example/faux"
    r = check(rapport, KNOWN_URLS)
    assert any("inventée" in e for e in r.errors), "Une URL absente de la collecte doit être refusée"


def test_url_inventee_dans_les_nouveautes_ecommerce(rapport):
    rapport["ecommerce"]["nouveautes"][0]["source_url"] = "https://inventé.example/x"
    r = check(rapport, KNOWN_URLS)
    assert any("inventée" in e for e in r.errors)


# ── Les erreurs qui casseraient l'affichage ───────────────────────────────────

def test_section_manquante(rapport):
    del rapport["ecommerce"]
    r = check(rapport, KNOWN_URLS)
    assert any("ecommerce" in e for e in r.errors)


def test_indicateur_de_recession_manquant(rapport):
    del rapport["market"]["recession_indicators"]["housing"]
    r = check(rapport, KNOWN_URLS)
    assert any("housing" in e for e in r.errors)


def test_valeurs_hors_liste_refusees(rapport):
    rapport["crypto"]["direction"] = "TRÈS HAUSSIER"
    rapport["market"]["regime"] = "Euphorie"
    rapport["ai"]["signals"][0]["sizing"] = "Énorme"
    rapport["deeptech"]["signals"][0]["horizon"] = "1-2"
    r = check(rapport, KNOWN_URLS)
    joined = " ".join(r.errors)
    assert "direction" in joined and "regime" in joined and "sizing" in joined and "horizon" in joined


def test_conviction_hors_bornes(rapport):
    rapport["ai"]["signals"][0]["conviction"] = 9
    r = check(rapport, KNOWN_URLS)
    assert any("conviction" in e for e in r.errors)


# ── Les erreurs de qualité rédactionnelle ─────────────────────────────────────

def test_explication_trop_courte_est_refusee(rapport):
    """Badr n'est pas expert : un 'fait' bâclé ne lui apprend rien."""
    rapport["ai"]["signals"][0]["fait"] = "Il s'est passé un truc."
    r = check(rapport, KNOWN_URLS)
    assert any("trop court" in e for e in r.errors)


def test_markdown_dans_le_texte_est_refuse(rapport):
    rapport["ai"]["signals"][0]["implication_2"] = "**Gras** interdit ici" + MID
    r = check(rapport, KNOWN_URLS)
    assert any("markdown" in e for e in r.errors)


def test_note_na_refusee_dans_le_score_crypto(rapport):
    rapport["crypto"]["score"]["macro"]["note"] = "N/A"
    r = check(rapport, KNOWN_URLS)
    assert any("N/A" in e for e in r.errors)


def test_themes_ecommerce_doivent_etre_differents(rapport):
    for sig in rapport["ecommerce"]["signals"]:
        sig["theme"] = "automation"
    r = check(rapport, KNOWN_URLS)
    assert any("DIFFÉRENTS" in e for e in r.errors)


def test_quatre_a_cinq_signaux_acceptes(rapport):
    """Badr veut plus de contenu : 4 ou 5 signaux par section doivent passer."""
    rapport["ai"]["signals"].append(_signal(URL_B))
    rapport["ai"]["signals"].append(_signal(URL_C))
    r = check(rapport, KNOWN_URLS)
    assert not any("ai.signals" in e for e in r.errors)


def test_six_signaux_refuses(rapport):
    rapport["ai"]["signals"] += [_signal(URL_B)] * 3
    r = check(rapport, KNOWN_URLS)
    assert any("ai.signals" in e for e in r.errors)


# ── Les nouvelles sections : outils, repos tendances, autres news ─────────────

def test_url_inventee_dans_les_outils(rapport):
    rapport["ecommerce"]["outils"][0]["source_url"] = "https://inventé.example/outil"
    r = check(rapport, KNOWN_URLS)
    assert any("outils[1]" in e and "inventée" in e for e in r.errors)


def test_categorie_outil_invalide(rapport):
    rapport["ecommerce"]["outils"][0]["categorie"] = "magie"
    r = check(rapport, KNOWN_URLS)
    assert any("categorie invalide" in e for e in r.errors)


def test_outil_sans_comment_tester(rapport):
    del rapport["ecommerce"]["outils"][0]["comment_tester"]
    r = check(rapport, KNOWN_URLS)
    assert any("comment_tester" in e for e in r.errors)


def test_categories_outils_alignees_avec_le_scout():
    from agents.scout_tools import USAGES
    from cowork_check import TOOL_CATEGORIES
    assert set(USAGES) == TOOL_CATEGORIES


def test_repo_tendance_type_invalide(rapport):
    rapport["ai"]["trending_repos"][0]["type"] = "site"
    r = check(rapport, KNOWN_URLS)
    assert any("trending_repos[1]" in e and "type invalide" in e for e in r.errors)


def test_autres_news_url_inventee(rapport):
    rapport["market"]["autres_news"][0]["source_url"] = "https://faux.example/x"
    r = check(rapport, KNOWN_URLS)
    assert any("market.autres_news[1]" in e and "inventée" in e for e in r.errors)


def test_autres_news_explication_trop_courte(rapport):
    rapport["crypto"]["autres_news"][0]["en_clair"] = "Bitcoin monte."
    r = check(rapport, KNOWN_URLS)
    assert any("crypto.autres_news[1]" in e and "trop court" in e for e in r.errors)


def test_sections_nouvelles_absentes_sont_un_avertissement_pas_une_erreur(rapport):
    """Un rapport de l'ancien format doit encore passer — avec des avertissements."""
    for sector in ("ai", "crypto", "market", "deeptech", "ecommerce"):
        rapport[sector].pop("autres_news", None)
    rapport["ai"].pop("trending_repos")
    rapport["ecommerce"].pop("outils")
    r = check(rapport, KNOWN_URLS)
    assert not r.errors, r.errors
    assert any("autres_news" in w for w in r.warnings)
    assert any("outils" in w for w in r.warnings)
    assert any("trending_repos" in w for w in r.warnings)


def _radar_item(**extra):
    item = {
        "produit": "Lampe pliable", "boutique": "lampe.com", "niche": "Maison", "prix": "39.9 USD",
        "statut": "BANGER", "signal": "La courbe monte.", "stade_marche": "Fenêtre ouverte.",
        "notoriete": "Personne en France.", "ca_jour_estime": "Estimation : 500-1 500 €/jour.",
        "difficulte": "moyen", "difficulte_pourquoi": "Prix sous l'AOV.", "marche_fr": "A VERIFIER",
        "marche_fr_detail": "Non vérifié.", "ou_lancer": "FR d'abord si libre, sinon DE.",
        "criteres_ok": ["besoin fort"], "criteres_ko": ["marge"],
        "verdict": "GO TEST", "verdict_pourquoi": "Parce que.", "budget_test": "200-600 € sur 48 h",
        "lien_boutique": "https://lampe.com", "lien_adlibrary": "https://www.facebook.com/ads/library/?q=lampe",
    }
    item.update(extra)
    return item


def test_radar_produit_complet_accepte(rapport):
    rapport["ecommerce"]["radar_produits"] = [_radar_item()]
    r = check(rapport, KNOWN_URLS)
    assert not any("radar_produits" in e for e in r.errors), r.errors


def test_radar_produits_incomplet(rapport):
    rapport["ecommerce"]["radar_produits"] = [{"produit": "Lampe", "niche": "Déco"}]
    r = check(rapport, KNOWN_URLS)
    assert any("radar_produits[1]" in e for e in r.errors)


def test_radar_valeurs_imposees(rapport):
    rapport["ecommerce"]["radar_produits"] = [_radar_item(verdict="ACHETER", marche_fr="LIBRE?", difficulte="dur")]
    r = check(rapport, KNOWN_URLS)
    joined = " ".join(r.errors)
    assert "verdict" in joined and "marche_fr" in joined and "difficulte" in joined


def test_radar_marche_fr_pris_sans_autre_marche_refuse(rapport):
    """MASTER RESEARCH · 3 : pas une pépite si quelqu'un l'a déjà lancé sur TON marché."""
    rapport["ecommerce"]["radar_produits"] = [_radar_item(marche_fr="PRIS", marche_fr_detail="Cabaïa, 1 844 pubs",
                                                          marches={"FR": "PRIS", "DE": "PRIS", "ES": "A VERIFIER"})]
    r = check(rapport, KNOWN_URLS)
    assert any("PRIS" in e and "ton marché" in e for e in r.errors)


def test_radar_marche_fr_pris_mais_allemagne_libre_accepte(rapport):
    """Cas GroundGuard (24/08) : France prise par Solina → DE + AT + CH."""
    rapport["ecommerce"]["radar_produits"] = [_radar_item(marche_fr="PRIS", marche_fr_detail="Solina, 10 pubs",
                                                          marches={"FR": "PRIS", "DE": "LIBRE", "ES": "A VERIFIER", "GB": "PRIS"},
                                                          ou_lancer="Allemagne d'abord : 0 pub sur Arbeitssocken.")]
    r = check(rapport, KNOWN_URLS)
    assert not any("radar_produits" in e for e in r.errors), r.errors


def test_radar_zero_resultat_jamais_libre_sans_detail(rapport):
    """FILTRES.md §6 : un 0 résultat s'écrit A VERIFIER, jamais LIBRE."""
    rapport["ecommerce"]["radar_produits"] = [_radar_item(marche_fr="LIBRE", marche_fr_detail="")]
    r = check(rapport, KNOWN_URLS)
    assert any("LIBRE" in e for e in r.errors)


def test_chiffres_vides_signales():
    from cowork_check import check_donnees
    vides = {"crypto_dashboard": {"btc_price": 0}, "market_dashboard": {"sp500": {"price": "N/A"}},
             "ecommerce_dashboard": {"stocks": []}}
    assert len(check_donnees(vides)) == 3
    pleins = {"crypto_dashboard": {"btc_price": 80000}, "market_dashboard": {"sp500": {"price": "7,700"}},
              "ecommerce_dashboard": {"stocks": [{"ticker": "SHOP"}]}}
    assert check_donnees(pleins) == []


# ── Publication ───────────────────────────────────────────────────────────────

def test_les_chiffres_sont_reinjectes_jamais_retapes(rapport):
    """Un prix inventé par le modèle doit être écrasé par la valeur relevée."""
    from cowork_publish import _merge_dashboards

    rapport["crypto"]["dashboard"] = {"btc_price": 999999}  # valeur fantaisiste
    donnees = {
        "crypto_dashboard": {"btc_price": 63312, "fear_greed_score": 27},
        "market_dashboard": {"sp500": {"price": "7,751", "change_pct": 0.3}},
        "market_hot_stocks": [{"ticker": "NVDA"}],
        "market_crash": {"crash_score": 2.5},
        "ecommerce_dashboard": {"stocks": [{"nom": "Shopify", "ticker": "SHOP",
                                            "price": 120.0, "change_pct": 1.0}]},
        "ecommerce_themes": {"automation": 3},
    }
    merged = _merge_dashboards(copy.deepcopy(rapport), donnees)

    assert merged["crypto"]["dashboard"]["btc_price"] == 63312, "Le chiffre relevé doit primer"
    assert merged["market"]["hot_stocks"] == [{"ticker": "NVDA"}]
    assert merged["ecommerce"]["dashboard"]["stocks"][0]["ticker"] == "SHOP"


def test_les_chiffres_radar_sont_reinjectes(rapport, tmp_path, monkeypatch):
    """Les ads actives, la courbe, l'âge… viennent du scan du jour, jamais du texte."""
    import json
    from agents import radar_produits
    from cowork_publish import _merge_dashboards

    monkeypatch.setattr(radar_produits, "RADAR_DIR", tmp_path)
    (tmp_path / "2026-08-29.json").write_text(json.dumps([{
        "boutique": "lampe.com", "ads_actives": 170, "courbe_ads": "25 > 128", "acceleration": 5.1,
        "age_jours": 11, "semaines_diffusion": 2, "visites_mois": 0, "pays_pub": "GB 39%", "nb_skus": 3,
        "prix": "45 USD", "statut": "BANGER",
    }]), encoding="utf-8")
    rapport["ecommerce"]["radar_produits"] = [_radar_item(boutique="lampe.com")]
    merged = _merge_dashboards(copy.deepcopy(rapport), {"date": "2026-08-29"})
    chiffres = merged["ecommerce"]["radar_produits"][0]["chiffres"]
    assert chiffres["ads_actives"] == 170 and chiffres["courbe_ads"] == "25 > 128" and chiffres["age_jours"] == 11


def test_les_cinq_messages_se_construisent(rapport):
    from cowork_publish import build_messages, _merge_dashboards

    merged = _merge_dashboards(copy.deepcopy(rapport), {})
    messages = build_messages(merged)
    assert len(messages) == 5
    for i, msg in enumerate(messages, 1):
        assert len(msg) > 400, f"Message {i} anormalement court"
    assert "E-COMMERCE" in messages[4]
