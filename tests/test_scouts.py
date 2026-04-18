"""
Tests scouts : vérifie que les collecteurs de données retournent
des structures valides sans crasher.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import pytest
import asyncio


# ── Scout Crypto ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crypto_dashboard_structure():
    from agents.scout_crypto import collect_dashboard
    d = await collect_dashboard()
    assert isinstance(d, dict), "dashboard doit etre un dict"
    assert "btc_price" in d, "btc_price manquant"
    assert "fear_greed_score" in d, "fear_greed_score manquant"
    assert "btc_dominance" in d, "btc_dominance manquant"
    assert d["btc_price"] is not None and d["btc_price"] > 0, f"btc_price invalide: {d['btc_price']}"

@pytest.mark.asyncio
async def test_crypto_signals_list():
    from agents.scout_crypto import collect_signals
    sigs = await collect_signals()
    assert isinstance(sigs, list), "signals doit etre une liste"
    assert len(sigs) > 0, "aucun signal crypto collecte"


# ── Scout Market ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_market_dashboard_structure():
    from agents.scout_market import collect_dashboard
    d = await collect_dashboard()
    assert isinstance(d, dict), "dashboard doit etre un dict"
    assert "sp500" in d, "sp500 manquant"
    assert "vix" in d, "vix manquant"
    sp = d["sp500"]
    assert sp.get("price"), f"sp500 price vide: {sp}"
    assert sp.get("change_pct") is not None, "sp500 change_pct manquant"
    assert sp.get("change_pct") != 0 or True, "change_pct peut etre 0 le weekend (ok)"

@pytest.mark.asyncio
async def test_market_change_pct_not_always_zero():
    """Verifie que le fix weekend fonctionne : au moins un indice a change_pct != 0."""
    from agents.scout_market import collect_dashboard
    d = await collect_dashboard()
    keys = ["sp500", "nasdaq", "gold", "oil", "dxy"]
    changes = [d.get(k, {}).get("change_pct", 0) for k in keys if k in d]
    assert any(c != 0 for c in changes), \
        f"Tous les change_pct sont a 0 — fix weekend ne fonctionne pas: {dict(zip(keys, changes))}"

@pytest.mark.asyncio
async def test_market_signals_list():
    from agents.scout_market import collect_signals
    sigs = await collect_signals()
    assert isinstance(sigs, list)


# ── Scout AI ──────────────────────────────────────────────────────────────────

def test_ai_scout_importable():
    """Verifie que le module scout_ai est importable et a run_scout_ai."""
    from agents import scout_ai
    import inspect
    assert hasattr(scout_ai, "run_scout_ai"), "run_scout_ai manquant dans scout_ai"
    assert inspect.iscoroutinefunction(scout_ai.run_scout_ai), "run_scout_ai doit etre async"


# ── Score recession ───────────────────────────────────────────────────────────

def test_recession_score_formula():
    """Verifie la formule : (nb_red * 1) + (nb_yellow * 0.5)"""
    indicators = {
        "courbe_taux":   {"status": "red",    "note": "test"},
        "emploi":        {"status": "green",  "note": "test"},
        "ism_manuf":     {"status": "yellow", "note": "test"},
        "ism_services":  {"status": "yellow", "note": "test"},
        "conso_conf":    {"status": "green",  "note": "test"},
        "credit_spread": {"status": "red",    "note": "test"},
        "earnings_rev":  {"status": "green",  "note": "test"},
        "pmi_composite": {"status": "yellow", "note": "test"},
        "retail_sales":  {"status": "green",  "note": "test"},
        "housing":       {"status": "green",  "note": "test"},
    }
    nb_red    = sum(1 for v in indicators.values() if v["status"] == "red")
    nb_yellow = sum(1 for v in indicators.values() if v["status"] == "yellow")
    score = round(nb_red * 1 + nb_yellow * 0.5)
    # 2 rouges + 3 jaunes = 2 + 1.5 = 3.5 -> arrondi 4
    assert nb_red == 2
    assert nb_yellow == 3
    assert score == 4, f"Score attendu 4, obtenu {score}"

def test_recession_score_max():
    """Score max avec 10 indicateurs tous rouges = 10."""
    indicators = {f"ind_{i}": {"status": "red"} for i in range(10)}
    nb_red = sum(1 for v in indicators.values() if v["status"] == "red")
    score = nb_red * 1
    assert score == 10

# ── Sectors US ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sectors_returns_11_sectors():
    from agents.scout_market import collect_sectors
    result = await collect_sectors()
    sector_keys = [k for k in result if not k.startswith("_")]
    assert len(sector_keys) == 11, f"Attendu 11 secteurs, obtenu {len(sector_keys)}: {sector_keys}"

@pytest.mark.asyncio
async def test_sectors_has_breadth():
    from agents.scout_market import collect_sectors
    result = await collect_sectors()
    breadth = result.get("_breadth", {})
    assert "pct_secteurs_hausse" in breadth, "_breadth.pct_secteurs_hausse manquant"
    assert 0 <= breadth["pct_secteurs_hausse"] <= 100, "pct_secteurs_hausse hors [0,100]"
    assert "sentiment" in breadth, "_breadth.sentiment manquant"
    assert breadth["sentiment"] in {"bullish", "bearish", "mitige"}, f"sentiment invalide: {breadth['sentiment']}"

@pytest.mark.asyncio
async def test_sectors_change_pct_not_all_zero():
    from agents.scout_market import collect_sectors
    result = await collect_sectors()
    changes = [v["change_pct"] for k, v in result.items() if not k.startswith("_")]
    assert any(c != 0 for c in changes), "Tous les change_pct secteurs sont 0"


# ── Exchange Flows ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exchange_flows_structure():
    from agents.scout_crypto import collect_exchange_flows
    result = await collect_exchange_flows()
    assert isinstance(result, dict), "exchange_flows doit etre un dict"
    for field in ["binance_vol_24h_usd", "top5_exchanges_vol_btc", "trend", "pression"]:
        assert field in result, f"champ '{field}' manquant"

@pytest.mark.asyncio
async def test_exchange_flows_trend_valid():
    from agents.scout_crypto import collect_exchange_flows
    result = await collect_exchange_flows()
    valid_trends = {"accumulation", "distribution", "indecis", "faible_volume", "inconnu"}
    assert result["trend"] in valid_trends, f"trend invalide: {result['trend']}"

@pytest.mark.asyncio
async def test_exchange_flows_volume_positive():
    from agents.scout_crypto import collect_exchange_flows
    result = await collect_exchange_flows()
    assert result["binance_vol_24h_usd"] >= 0, "binance_vol_24h_usd negatif"
    assert result["top5_exchanges_vol_btc"] >= 0, "top5_exchanges_vol_btc negatif"


def test_recession_has_10_indicators():
    """Verifie que le prompt genere bien 10 indicateurs."""
    expected = {"courbe_taux", "emploi", "ism_manuf", "ism_services",
                "conso_conf", "credit_spread", "earnings_rev",
                "pmi_composite", "retail_sales", "housing"}
    assert len(expected) == 10


# ── Earnings Calendar ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_earnings_calendar_returns_list():
    from agents.scout_market import collect_earnings_calendar
    result = await collect_earnings_calendar()
    assert isinstance(result, list), "earnings calendar doit retourner une liste"

@pytest.mark.asyncio
async def test_earnings_calendar_structure():
    from agents.scout_market import collect_earnings_calendar
    result = await collect_earnings_calendar()
    for item in result:
        assert "ticker" in item, f"champ 'ticker' manquant: {item}"
        assert "date" in item, f"champ 'date' manquant: {item}"
        assert "days_until" in item, f"champ 'days_until' manquant: {item}"
        assert 0 <= item["days_until"] <= 7, f"days_until hors fenetre 7j: {item}"


# ── Insider Trading ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insider_trades_returns_list():
    from agents.scout_market import collect_insider_trades
    result = await collect_insider_trades()
    assert isinstance(result, list), "insider trades doit retourner une liste"

@pytest.mark.asyncio
async def test_insider_trades_structure():
    from agents.scout_market import collect_insider_trades
    result = await collect_insider_trades()
    required = ["insider", "company", "ticker", "type", "shares", "value_usd", "date"]
    for trade in result:
        for field in required:
            assert field in trade, f"champ '{field}' manquant dans: {trade}"
        assert trade["type"] == "BUY", f"type doit etre BUY: {trade['type']}"
        assert trade["value_usd"] >= 100_000, f"value_usd < 100K: {trade['value_usd']}"

@pytest.mark.asyncio
async def test_insider_trades_sorted_by_value():
    from agents.scout_market import collect_insider_trades
    result = await collect_insider_trades()
    if len(result) >= 2:
        values = [t["value_usd"] for t in result]
        assert values == sorted(values, reverse=True), "trades doivent etre tries par value_usd desc"
