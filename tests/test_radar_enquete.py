"""Tests de l'enquête radar — sans réseau : intensité des douleurs et tri."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.radar_enquete import intensite, trier_douleurs, _strip_html, format_md


def test_douleur_forte_detectee():
    niveau, marqueurs = intensite("Ça fait 3 mois, j'ai tout essayé, je n'en peux plus, c'est un cauchemar")
    assert niveau == "forte" and "cauchemar" in marqueurs


def test_douleur_moyenne_et_faible():
    assert intensite("C'est un peu agaçant le matin")[0] == "moyenne"
    assert intensite("Quelqu'un connaît une bonne marque ?")[0] == "faible"


def test_tri_fortes_d_abord_et_doublons():
    posts = [
        {"url": "u1", "score": 2, "commentaires": 0, "intensite": "faible"},
        {"url": "u2", "score": 1, "commentaires": 0, "intensite": "forte"},
        {"url": "u3", "score": 50, "commentaires": 10, "intensite": "moyenne"},
        {"url": "u2", "score": 1, "commentaires": 0, "intensite": "forte"},
    ]
    out = trier_douleurs(posts)
    assert [p["url"] for p in out] == ["u2", "u3"], "forte d'abord, faible sous le score minimum écartée, doublon retiré"


def test_strip_html():
    assert _strip_html("<p>Bonjour&nbsp;<b>toi</b></p>") == "Bonjour  toi"


def test_format_md_sans_fiche():
    md = format_md([{"boutique": "x.com", "produit": "P", "fiche": {"erreur": "HTTP 404"},
                     "douleurs": [], "compte": {"posts": 0, "fortes": 0}}], "2026-08-29")
    assert "indisponible (HTTP 404)" in md and "## P — x.com" in md
