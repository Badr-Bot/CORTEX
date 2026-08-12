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


@pytest.fixture
def rapport():
    return {
        "ai": {
            "signals": [_signal(URL_A), _signal(URL_B), _signal(URL_C)],
            "watchlist": ["Premier signal à surveiller", "Deuxième signal à confirmer"],
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
        },
        "deeptech": {"signals": [_deeptech_signal(URL_A), _deeptech_signal(URL_B)]},
        "ecommerce": {
            "tendance_globale": "Ce qui bouge en e-commerce en ce moment, expliqué simplement.",
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


def test_les_cinq_messages_se_construisent(rapport):
    from cowork_publish import build_messages, _merge_dashboards

    merged = _merge_dashboards(copy.deepcopy(rapport), {})
    messages = build_messages(merged)
    assert len(messages) == 5
    for i, msg in enumerate(messages, 1):
        assert len(msg) > 400, f"Message {i} anormalement court"
    assert "E-COMMERCE" in messages[4]
