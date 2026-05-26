"""
CORTEX — Déduplication des signaux (7 jours glissants)

Stocke les hashes de titres dans data/dedup_cache.json.
Un signal revu cette semaine reçoit un tag "Tendance persistante".
Un signal vu 3+ fois est ignoré sauf s'il reste unique dans son secteur.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

CACHE_FILE = Path(__file__).parent.parent / "data" / "dedup_cache.json"
WINDOW_DAYS = 7
SKIP_THRESHOLD = 3


def _load() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(title: str) -> str:
    return hashlib.md5(title.lower().strip()[:80].encode()).hexdigest()[:12]


def _purge_old(cache: dict) -> dict:
    cutoff = (datetime.now() - timedelta(days=WINDOW_DAYS)).isoformat()
    cleaned = {}
    for k, dates in cache.items():
        recent = [d for d in dates if d >= cutoff]
        if recent:
            cleaned[k] = recent
    return cleaned


def check(title: str) -> tuple[str, int]:
    """
    Returns (status, seen_count):
      "new"        — jamais vu cette semaine
      "persistent" — vu 1-2 fois, toujours pertinent (à tagger)
      "skip"       — vu 3+ fois, à ignorer
    """
    cache = _purge_old(_load())
    key = _hash(title)
    seen = len(cache.get(key, []))
    if seen == 0:
        return "new", 0
    if seen >= SKIP_THRESHOLD:
        return "skip", seen
    return "persistent", seen


def register(title: str) -> None:
    """Marque un signal comme vu aujourd'hui."""
    cache = _purge_old(_load())
    key = _hash(title)
    if key not in cache:
        cache[key] = []
    cache[key].append(datetime.now().isoformat())
    _save(cache)


def filter_signals(signals: list[dict], title_key: str = "title") -> list[dict]:
    """
    Filtre une liste de signaux :
    - "new"        → conservé tel quel
    - "persistent" → conservé avec dedup_tag ajouté
    - "skip"       → ignoré (sauf si c'est le seul signal du lot)

    Garantit qu'au moins 1 signal passe même si tous sont "skip".
    """
    result = []
    skipped = []

    for sig in signals:
        title = sig.get(title_key, "")
        status, count = check(title)
        if status == "skip":
            skipped.append(sig)
            continue
        sig = dict(sig)
        if status == "persistent":
            sig["dedup_tag"] = f"⟳ Tendance persistante ({count}j)"
        result.append(sig)

    # Garantie minimale : au moins 1 signal
    if not result and skipped:
        result = [skipped[0]]

    return result


def mark_sent(signals: list[dict], title_key: str = "title") -> None:
    """Enregistre tous les signaux envoyés comme vus aujourd'hui."""
    for sig in signals:
        title = sig.get(title_key, "")
        if title:
            register(title)
