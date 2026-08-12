"""
Tests des alertes marché (agents/alert_monitor.py).

Réécrits le 2026-08-12 : l'ancienne version testait une API disparue lors du
refactor de mai (nexus, agents.memory, _STATE_FILE fichier local, job
alert_monitor dans APScheduler). Les alertes tournent désormais sur GitHub
Actions et le cooldown vit dans Supabase.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import inspect

import pytest


# ── Alert Monitor ─────────────────────────────────────────────────────────────

def test_alert_monitor_importable():
    from agents.alert_monitor import check_and_send_alerts, MARKET_THRESHOLDS
    assert callable(check_and_send_alerts)
    assert len(MARKET_THRESHOLDS) >= 4, "Moins de 4 seuils définis"


def test_alert_thresholds_keys():
    from agents.alert_monitor import MARKET_THRESHOLDS
    required_keys = {"vix_spike", "btc_crash", "btc_rally", "sp500_chute"}
    missing = required_keys - set(MARKET_THRESHOLDS.keys())
    assert not missing, f"Seuils manquants: {missing}"
    for key, cfg in MARKET_THRESHOLDS.items():
        assert "label" in cfg, f"{key} manque 'label'"
        assert "emoji" in cfg, f"{key} manque 'emoji'"
        assert cfg.get("cooldown_h", 0) >= 1, f"{key} cooldown trop court"


def test_alert_cooldown_signature():
    """Le cooldown est stocké dans Supabase et prend (key, hours)."""
    from agents.alert_monitor import _is_in_cooldown
    params = list(inspect.signature(_is_in_cooldown).parameters)
    assert params == ["key", "hours"], f"Signature inattendue: {params}"


def test_alert_news_key_is_stable_and_short():
    from agents.alert_monitor import _news_key
    k1 = _news_key("https://example.com/article-1")
    k2 = _news_key("https://example.com/article-1")
    k3 = _news_key("https://example.com/article-2")
    assert k1 == k2, "La clé doit être stable pour une même URL"
    assert k1 != k3, "Deux URLs différentes doivent donner des clés différentes"
    assert len(k1) <= 20


@pytest.mark.asyncio
async def test_alert_fetch_snapshot_returns_dict():
    from agents.alert_monitor import _fetch_market_snapshot
    snap = await _fetch_market_snapshot()
    assert isinstance(snap, dict), "snapshot doit etre un dict"
    assert len(snap) >= 1, "snapshot vide"
    for key, data in snap.items():
        assert "price" in data, f"snapshot[{key}] manque 'price'"
        assert "change_pct" in data, f"snapshot[{key}] manque 'change_pct'"


def test_alert_feeds_have_no_dead_reuters_domain():
    """feeds.reuters.com ne résout plus — il ne doit plus être référencé."""
    from agents.alert_monitor import NEWS_FEEDS
    for feed in NEWS_FEEDS:
        assert "feeds.reuters.com" not in feed["url"], \
            f"Flux mort référencé: {feed['name']}"
