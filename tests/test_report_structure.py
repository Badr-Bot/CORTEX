"""
Tests structure du rapport : vérifie que report_json contient
tous les champs attendus pour le dashboard.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import pytest


def _get_latest_report():
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    res = sb.table("daily_reports").select("*").order("report_date", desc=True).limit(1).execute()
    assert res.data, "Aucun rapport dans Supabase"
    return res.data[0]["report_json"]


def test_report_has_all_sectors():
    rj = _get_latest_report()
    for sector in ["ai", "crypto", "market", "deeptech", "nexus"]:
        assert sector in rj, f"Secteur '{sector}' manquant dans report_json"


def test_crypto_section_not_na():
    rj = _get_latest_report()
    c = rj.get("crypto", {})
    assert c.get("phase") not in [None, "", "N/A"], f"crypto.phase = N/A ou vide: {c.get('phase')}"
    assert c.get("direction") not in [None, "", "N/A"], f"crypto.direction = N/A ou vide"
    assert isinstance(c.get("score"), dict) and len(c["score"]) > 0, "crypto.score vide"
    d = c.get("dashboard", {})
    assert d.get("btc_price") and d["btc_price"] > 0, f"btc_price invalide: {d.get('btc_price')}"


def test_market_has_percentages():
    rj = _get_latest_report()
    m = rj.get("market", {})
    dash = m.get("dashboard", {})
    for key in ["sp500", "nasdaq"]:
        item = dash.get(key, {})
        assert item.get("price"), f"{key}.price vide"
        assert item.get("change_pct") is not None, f"{key}.change_pct manquant"


def test_market_has_10_recession_indicators():
    rj = _get_latest_report()
    indicators = rj.get("market", {}).get("recession_indicators", {})
    assert len(indicators) == 10, f"Attendu 10 indicateurs, obtenu {len(indicators)}: {list(indicators.keys())}"


def test_nexus_has_question():
    rj = _get_latest_report()
    n = rj.get("nexus", {})
    assert n.get("question") not in [None, ""], "nexus.question vide"
    assert "has_connexion" in n, "nexus.has_connexion manquant"


def test_signals_have_required_fields():
    rj = _get_latest_report()
    required = ["title", "fait", "action", "sizing", "conviction", "invalide_si"]
    for sector in ["ai", "crypto", "market"]:
        signals = rj.get(sector, {}).get("signals", [])
        assert len(signals) > 0, f"Aucun signal pour {sector}"
        for sig in signals:
            for field in required:
                assert field in sig and sig[field], f"{sector} signal manque '{field}': {sig.get('title')}"


def test_sizing_values_valid():
    rj = _get_latest_report()
    valid = {"Fort", "Moyen", "Faible"}
    for sector in ["ai", "crypto", "market"]:
        for sig in rj.get(sector, {}).get("signals", []):
            assert sig.get("sizing") in valid, \
                f"{sector} signal sizing invalide: '{sig.get('sizing')}' (attendu: {valid})"


def test_conviction_range():
    rj = _get_latest_report()
    for sector in ["ai", "crypto", "market", "deeptech"]:
        for sig in rj.get(sector, {}).get("signals", []):
            c = sig.get("conviction", 0)
            assert 1 <= c <= 5, f"{sector} conviction hors range: {c}"
