"""Le contrôle pays par la Meta Ad Library (gratuit) : LIBRE / PARTIEL / PRIS."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.radar_produits import analyser_marche_meta  # noqa: E402

NOW = 1_788_000_000  # 2026-08-29 environ


def _ad(page, days_ago, titre=""):
    return {"id": "x", "page_id": hash(page) % 10**9, "page_name": page,
            "ad_creation_time": NOW - days_ago * 86400, "ad_creative_link_title": titre}


def _payload(ads, total=None):
    return {"results": json.dumps({"estimated_total_count": total if total is not None else len(ads), "ads": ads})}


def test_marche_libre_quand_aucune_pub():
    res = analyser_marche_meta(_payload([], total=0), NOW)
    assert res["verdict"] == "LIBRE" and res["stade"] == 1


def test_marche_partiel_avec_trois_petits_annonceurs_recents():
    ads = [_ad("Brenf", 10, "Toutes les solutions pour souris ont échoué")] * 3 + [_ad("Lyra", 5)] * 2 + [_ad("EchoProtect", 120)]
    res = analyser_marche_meta(_payload(ads), NOW)
    assert res["verdict"] == "PARTIEL" and res["stade"] == 2
    assert res["nb_annonceurs"] == 3
    brenf = next(p for p in res["annonceurs"] if p["page"] == "Brenf")
    assert brenf["ads"] == 3 and brenf["recent"] is True and "souris" in brenf["exemple"]
    echo = next(p for p in res["annonceurs"] if p["page"] == "EchoProtect")
    assert echo["recent"] is False


def test_marche_pris_avec_cinq_annonceurs():
    ads = [_ad(f"Shop{i}", 30) for i in range(5)]
    res = analyser_marche_meta(_payload(ads), NOW)
    assert res["verdict"] == "PRIS" and res["stade"] == 3


def test_marche_pris_avec_un_acteur_dominant():
    ads = [_ad("Urban Core Hub", 40)] * 25 + [_ad("Petit", 3)]
    res = analyser_marche_meta(_payload(ads), NOW)
    assert res["verdict"] == "PRIS" and "dominant" in res["raison"] and "Urban Core Hub" in res["raison"]


def test_accepte_le_json_deja_decode():
    res = analyser_marche_meta({"estimated_total_count": 2, "ads": [_ad("A", 1), _ad("A", 2)]}, NOW)
    assert res["verdict"] == "PARTIEL" and res["annonceurs"][0]["ads"] == 2
