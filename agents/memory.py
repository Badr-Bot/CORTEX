"""
CORTEX — Memory System
Sauvegarde l'analyse quotidienne de chaque secteur dans Supabase
et charge l'historique des 7 derniers jours pour enrichir le contexte
des prompts Claude (éviter les répétitions, détecter les tendances).

Table Supabase requise : daily_analyses
  → Exécuter daily_analyses dans Supabase SQL Editor si la table est absente.
"""

import asyncio
import os
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("memory")

_TABLE = "daily_analyses"


# ── Client Supabase ───────────────────────────────────────────────────────────

def _get_client():
    """Retourne un client Supabase ou None si non disponible."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Supabase non disponible: {e}")
        return None


# ── Écriture ──────────────────────────────────────────────────────────────────

async def save_analysis(sector: str, data: dict) -> bool:
    """
    Sauvegarde l'analyse d'un secteur pour aujourd'hui dans Supabase.
    Si une analyse existe déjà pour ce secteur + cette date, elle est remplacée.

    Args:
        sector : 'ai' | 'crypto' | 'market' | 'deeptech' | 'nexus'
        data   : dict retourné par analyze_*() ou generate_nexus()
    """
    client = _get_client()
    if not client:
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    def _do_save():
        # Supprimer l'existant pour cet (sector, date)
        try:
            client.table(_TABLE).delete()\
                .eq("report_date", today)\
                .eq("sector", sector)\
                .execute()
        except Exception:
            pass
        # Insérer la nouvelle analyse
        client.table(_TABLE).insert({
            "report_date":    today,
            "sector":         sector,
            "analysis_json":  data,
        }).execute()

    try:
        await asyncio.to_thread(_do_save)
        logger.info(f"Mémoire [{sector}] sauvegardée — {today}")
        return True
    except Exception as e:
        logger.warning(f"Erreur save_analysis [{sector}]: {e}")
        return False


# ── Lecture ───────────────────────────────────────────────────────────────────

async def get_sector_history(sector: str, days: int = 7) -> list[dict]:
    """
    Charge l'historique d'un secteur pour les N derniers jours.

    Returns:
        Liste de {'report_date': str, 'data': dict}
        triée du plus récent au plus ancien.
        Liste vide si Supabase non disponible ou aucune donnée.
    """
    client = _get_client()
    if not client:
        return []

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    def _do_fetch():
        return (
            client.table(_TABLE)
            .select("report_date, analysis_json")
            .eq("sector", sector)
            .gte("report_date", cutoff)
            .order("report_date", desc=True)
            .limit(days)
            .execute()
        )

    try:
        result = await asyncio.to_thread(_do_fetch)
        rows = result.data or []
        return [
            {"report_date": r["report_date"], "data": r["analysis_json"]}
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"Erreur get_sector_history [{sector}]: {e}")
        return []


# ── Formatage du contexte pour les prompts ────────────────────────────────────

def format_ai_history(history: list[dict]) -> str:
    """
    Retourne un bloc de contexte compact sur les signaux IA des jours précédents.
    Utilisé pour éviter les redites et indiquer à Claude les tendances déjà couvertes.
    """
    if not history:
        return ""

    lines = ["── Signaux IA déjà couverts (ne pas répéter) ──"]
    for entry in history[:5]:
        date = entry["report_date"]
        signals = entry["data"].get("signals", [])
        if not signals:
            continue
        titles = " | ".join(s.get("title", "")[:55] for s in signals[:3])
        watchlist = entry["data"].get("watchlist", [])
        watch_str = ""
        if watchlist:
            watch_str = f" // watch: {watchlist[0][:35]}"
        lines.append(f"  {date}: {titles}{watch_str}")
    return "\n".join(lines) if len(lines) > 1 else ""


def format_crypto_history(history: list[dict]) -> str:
    """
    Retourne un contexte compact sur les tendances crypto des derniers jours.
    Permet à Claude de détecter les retournements et confirmer les tendances.
    """
    if not history:
        return ""

    lines = ["── Historique crypto récent ──"]
    for entry in history[:7]:
        date = entry["report_date"]
        data = entry["data"]
        direction = data.get("direction", "?")
        dashboard = data.get("dashboard", {})
        btc = dashboard.get("btc_price")
        fg  = dashboard.get("fear_greed_score", "?")
        phase = data.get("phase", "?")
        btc_str = f"${btc:,.0f}" if isinstance(btc, (int, float)) else f"${btc}"
        lines.append(f"  {date}: {direction} | BTC {btc_str} | F&G {fg} | {phase}")
    return "\n".join(lines) if len(lines) > 1 else ""


def format_market_history(history: list[dict]) -> str:
    """
    Retourne un contexte compact sur les tendances macro des derniers jours.
    """
    if not history:
        return ""

    lines = ["── Historique marchés récent ──"]
    for entry in history[:7]:
        date = entry["report_date"]
        data = entry["data"]
        regime  = data.get("regime", "?")
        rec     = data.get("recession_score", "?")
        sp_data = data.get("dashboard", {}).get("sp500", {})
        sp      = sp_data.get("price", "?") if isinstance(sp_data, dict) else "?"
        lines.append(f"  {date}: {regime} | Récession {rec}/10 | S&P {sp}")
    return "\n".join(lines) if len(lines) > 1 else ""


def format_deeptech_history(history: list[dict]) -> str:
    """
    Retourne un contexte compact sur les signaux deeptech déjà couverts.
    """
    if not history:
        return ""

    lines = ["── Signaux deeptech déjà couverts (ne pas répéter) ──"]
    for entry in history[:5]:
        date = entry["report_date"]
        signals = entry["data"].get("signals", [])
        for s in signals[:2]:
            title   = s.get("title", "")[:55]
            horizon = s.get("horizon", "?")
            lines.append(f"  {date}: {title} (horizon: {horizon})")
    return "\n".join(lines) if len(lines) > 1 else ""


# ── Learnings hebdomadaires ───────────────────────────────────────────────────

_LEARNINGS_TABLE = "agent_learnings"


async def get_agent_learnings(sector: str, limit: int = 5) -> list[dict]:
    """
    Récupère les N derniers apprentissages pour un secteur depuis Supabase.

    Args:
        sector : 'ai' | 'crypto' | 'market' | 'deeptech' | 'global'
        limit  : nombre max de learnings à récupérer
    Returns:
        Liste de {'week_of': str, 'learning': str, 'pattern': str}
    """
    client = _get_client()
    if not client:
        return []

    def _do_fetch():
        return (
            client.table(_LEARNINGS_TABLE)
            .select("week_of, learning, pattern, signal_title")
            .eq("sector", sector)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    try:
        result = await asyncio.to_thread(_do_fetch)
        return result.data or []
    except Exception as e:
        logger.warning(f"Erreur get_agent_learnings [{sector}]: {e}")
        return []


def format_learnings_context(learnings: list[dict], sector: str) -> str:
    """
    Formate les learnings en bloc de contexte injectables dans les prompts Claude.
    Aide l'agent à éviter les erreurs passées et intégrer les patterns détectés.

    Args:
        learnings : liste retournée par get_agent_learnings()
        sector    : label lisible pour l'en-tête
    Returns:
        Bloc texte à injecter en fin de system prompt, ou '' si vide
    """
    if not learnings:
        return ""

    lines = [f"── Apprentissages passés [{sector}] (intègre-les dans ton analyse) ──"]
    for item in learnings:
        week    = item.get("week_of", "?")
        learn   = item.get("learning", "").strip()
        pattern = item.get("pattern", "")
        if not learn:
            continue
        line = f"  [{week}] {learn}"
        if pattern:
            line += f"  (pattern: {pattern})"
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""
