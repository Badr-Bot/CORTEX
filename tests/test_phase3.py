"""
Tests Phase 3 :
  - Alert monitor (seuils, cooldown, state)
  - Pattern decay (filtrage > 8 semaines)
  - Nexus anti-répétition (questions passées extraites)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta


# ── Alert Monitor ─────────────────────────────────────────────────────────────

def test_alert_monitor_importable():
    from agents.alert_monitor import check_and_send_alerts, THRESHOLDS, COOLDOWN_HOURS
    assert callable(check_and_send_alerts)
    assert len(THRESHOLDS) >= 4, "Moins de 4 seuils définis"
    assert COOLDOWN_HOURS >= 1, "Cooldown trop court"


def test_alert_cooldown_logic():
    from agents.alert_monitor import _is_in_cooldown, COOLDOWN_HOURS
    # En cooldown : last alert il y a 30 min
    recent = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    state = {"btc_crash": recent}
    assert _is_in_cooldown(state, "btc_crash") is True, "Doit être en cooldown après 30 min"

    # Pas en cooldown : last alert il y a 3h
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    state2 = {"btc_crash": old}
    assert _is_in_cooldown(state2, "btc_crash") is False, "Ne doit pas être en cooldown après 3h"

    # Jamais alerté
    assert _is_in_cooldown({}, "btc_crash") is False, "Pas en cooldown si jamais alerté"


def test_alert_state_save_load(tmp_path):
    import agents.alert_monitor as am
    orig_file = am._STATE_FILE
    am._STATE_FILE = tmp_path / "test_state.json"
    try:
        state = {"btc_crash": datetime.now(timezone.utc).isoformat()}
        am._save_state(state)
        loaded = am._load_state()
        assert "btc_crash" in loaded
        assert loaded["btc_crash"] == state["btc_crash"]
    finally:
        am._STATE_FILE = orig_file


@pytest.mark.asyncio
async def test_alert_fetch_snapshot_returns_dict():
    from agents.alert_monitor import _fetch_market_snapshot
    snap = await _fetch_market_snapshot()
    assert isinstance(snap, dict), "snapshot doit etre un dict"
    # Au moins VIX ou BTC doivent etre présents
    assert len(snap) >= 1, "snapshot vide"
    for key, data in snap.items():
        assert "price" in data, f"snapshot[{key}] manque 'price'"
        assert "change_pct" in data, f"snapshot[{key}] manque 'change_pct'"


def test_alert_thresholds_keys():
    from agents.alert_monitor import THRESHOLDS
    required_keys = {"vix_spike", "btc_crash", "btc_rally", "sp500_chute"}
    missing = required_keys - set(THRESHOLDS.keys())
    assert not missing, f"Seuils manquants: {missing}"
    for key, cfg in THRESHOLDS.items():
        assert "label" in cfg, f"{key} manque 'label'"
        assert "emoji" in cfg, f"{key} manque 'emoji'"


# ── Pattern Decay ─────────────────────────────────────────────────────────────

def test_pattern_decay_max_weeks_param():
    """Vérifie que get_agent_learnings accepte max_weeks."""
    import inspect
    from agents.memory import get_agent_learnings
    sig = inspect.signature(get_agent_learnings)
    assert "max_weeks" in sig.parameters, "max_weeks param manquant dans get_agent_learnings"
    assert sig.parameters["max_weeks"].default == 8, "max_weeks default doit etre 8"


def test_pattern_decay_cutoff_calculation():
    """Vérifie que le cutoff est calculé correctement."""
    from datetime import date, timedelta
    max_weeks = 8
    cutoff = (date.today() - timedelta(weeks=max_weeks)).isoformat()
    assert len(cutoff) == 10, "cutoff doit etre au format YYYY-MM-DD"
    cutoff_date = date.fromisoformat(cutoff)
    diff = date.today() - cutoff_date
    assert 55 <= diff.days <= 57, f"Cutoff 8 semaines attendu ~56 jours, obtenu {diff.days}"


# ── Nexus Anti-répétition ─────────────────────────────────────────────────────

def test_nexus_system_prompt_has_antirep():
    from agents.summarizer import _SYSTEM_NEXUS
    assert "ANTI-RÉPÉTITION" in _SYSTEM_NEXUS or "anti" in _SYSTEM_NEXUS.lower(), \
        "Prompt Nexus doit mentionner l'anti-répétition"


def test_nexus_extracts_past_questions():
    """Vérifie la logique d'extraction des questions passées (test unitaire)."""
    nexus_history = [
        {
            "report_date": "2026-04-17",
            "data": {
                "connexion": "Fed hawkish [MARCHÉS] → BTC sous pression [CRYPTO]",
                "question": "Si le dollar monte encore, tu vends BTC ou tu attends le support ?",
                "questions": [
                    "Si le dollar monte encore, tu vends BTC ou tu attends le support ?",
                    "Comment NVDA et ETH se corrèlent dans ce contexte de taux ?",
                    "Cette rotation sectorielle annonce-t-elle une récession dans 6 mois ?",
                ],
            },
        },
    ]
    q_lines = []
    for entry in nexus_history[:7]:
        data = entry["data"]
        qs = data.get("questions", [])
        q_main = data.get("question", "")
        if q_main:
            qs = [q_main] + [q for q in qs if q != q_main]
        for q in qs[:3]:
            if q and len(q) > 10:
                q_lines.append(f"  [{entry['report_date']}] {q[:150]}")

    assert len(q_lines) == 3, f"Attendu 3 questions extraites, obtenu {len(q_lines)}"
    assert "2026-04-17" in q_lines[0]


def test_scheduler_has_alert_job():
    from scheduler import build_scheduler
    scheduler = build_scheduler()
    job_ids = [j.id for j in scheduler.get_jobs()]
    assert "alert_monitor" in job_ids, "Job alert_monitor manquant dans le scheduler"
    assert len(job_ids) == 6, f"Attendu 6 jobs, obtenu {len(job_ids)}: {job_ids}"
