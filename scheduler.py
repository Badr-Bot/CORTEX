"""
CORTEX — Scheduler de tâches planifiées
Utilise APScheduler avec AsyncIOScheduler
Timezone : Europe/Paris
"""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.logger import get_logger

logger = get_logger("scheduler")

# Timezone utilisée pour toutes les tâches
TIMEZONE = "Europe/Paris"


# ============================================================
# TÂCHES PLANIFIÉES
# ============================================================

async def run_morning_report() -> None:
    """
    Tâche quotidienne à 06:00 — Rapport CORTEX v2 complet (5 messages).
    IA + Crypto + Marchés + DeepTech + Nexus
    """
    try:
        from morning_report import run_morning_report as _run
        today = datetime.now().strftime("%d/%m/%Y")
        logger.info(f"Rapport CORTEX v2 déclenché — {today}")
        await _run(hours=24, send_telegram=True)
    except Exception as e:
        logger.error(f"Erreur run_morning_report : {e}")


async def run_agents() -> None:
    """
    Tâche quotidienne à 02:00 — Cycle de collecte des agents.
    Phase 1 : Simulation.
    Phase 2 (future) : Exécution des vrais agents SCOUTs.
    """
    try:
        today = datetime.now().strftime("%d/%m/%Y %H:%M")
        logger.info(f"Cycle agents simulé — {today}")
        # TODO Phase 2 : Implémenter les agents SCOUT ici
        # await oracle.run_collection_cycle()

    except Exception as e:
        logger.error(f"Erreur run_agents : {e}")


async def run_weekly_summary() -> None:
    """
    Tâche hebdomadaire — Dimanche à 20:00.
    Bilan de la semaine : évaluation des réponses de Badr, patterns détectés,
    learnings sauvegardés dans agent_learnings (Supabase).
    """
    try:
        from agents.weekly_bilan import run_weekly_bilan
        week = datetime.now().strftime("Semaine %W/%Y")
        logger.info(f"Bilan hebdomadaire CORTEX — {week}")
        await run_weekly_bilan()
    except Exception as e:
        logger.error(f"Erreur run_weekly_summary : {e}")


async def run_long_memory_compression() -> None:
    """
    Tâche hebdomadaire — Dimanche à 21:00 (après le bilan de 20:00).
    Filet de sécurité : si la compression dans weekly_bilan a échoué, on réessaie.
    En pratique, weekly_bilan.py déclenche déjà la compression en fin de bilan.
    """
    try:
        from agents.long_memory import run_weekly_compression
        from datetime import datetime, timedelta
        week_of = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        logger.info(f"Long memory compression (sécurité) — semaine {week_of}")
        await run_weekly_compression(week_of)
    except Exception as e:
        logger.error(f"Erreur run_long_memory_compression : {e}")


async def run_monthly_synthesis() -> None:
    """
    Tâche mensuelle — 1er du mois à 08:00.
    Phase 1 : Simulation.
    Phase 2 (future) : Synthèse mensuelle et compression des données.
    """
    try:
        month = datetime.now().strftime("%B %Y")
        logger.info(f"Synthèse mensuelle simulée — {month}")
        # TODO Phase 2 : Générer la synthèse mensuelle et archiver
        # await nexus.generate_monthly_synthesis()

    except Exception as e:
        logger.error(f"Erreur run_monthly_synthesis : {e}")


# ============================================================
# CONFIGURATION ET DÉMARRAGE DU SCHEDULER
# ============================================================

def build_scheduler() -> AsyncIOScheduler:
    """
    Construit et configure le scheduler avec tous les jobs.

    Returns:
        AsyncIOScheduler configuré (non démarré)
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # ── Job 1 : Rapport du matin — chaque jour à 06:00 ──────────────
    scheduler.add_job(
        func=run_morning_report,
        trigger=CronTrigger(hour=6, minute=0, timezone=TIMEZONE),
        id="morning_report",
        name="Rapport du matin",
        replace_existing=True,
        misfire_grace_time=300  # 5 min de tolérance si le système était down
    )

    # ── Job 2 : Cycle agents — chaque jour à 02:00 ──────────────────
    scheduler.add_job(
        func=run_agents,
        trigger=CronTrigger(hour=2, minute=0, timezone=TIMEZONE),
        id="agents_cycle",
        name="Cycle agents SCOUT",
        replace_existing=True,
        misfire_grace_time=300
    )

    # ── Job 3 : Résumé hebdomadaire — Dimanche à 20:00 ──────────────
    scheduler.add_job(
        func=run_weekly_summary,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=TIMEZONE),
        id="weekly_summary",
        name="Résumé hebdomadaire",
        replace_existing=True,
        misfire_grace_time=600
    )

    # ── Job 4 : Long memory compression — Dimanche à 21:00 ─────────
    scheduler.add_job(
        func=run_long_memory_compression,
        trigger=CronTrigger(day_of_week="sun", hour=21, minute=0, timezone=TIMEZONE),
        id="long_memory_compression",
        name="Long memory compression (sécurité)",
        replace_existing=True,
        misfire_grace_time=600
    )

    # ── Job 5 : Synthèse mensuelle — 1er du mois à 08:00 ────────────
    scheduler.add_job(
        func=run_monthly_synthesis,
        trigger=CronTrigger(day=1, hour=8, minute=0, timezone=TIMEZONE),
        id="monthly_synthesis",
        name="Synthèse mensuelle",
        replace_existing=True,
        misfire_grace_time=600
    )

    # Log des jobs configurés
    logger.info(f"Scheduler configuré — {len(scheduler.get_jobs())} jobs planifiés :")
    for job in scheduler.get_jobs():
        logger.info(f"  • {job.name} [{job.id}]")

    return scheduler


def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Démarre le scheduler.

    Args:
        scheduler: Scheduler configuré par build_scheduler()
    """
    try:
        scheduler.start()
        logger.info("Scheduler démarré — CORTEX en veille active")
    except Exception as e:
        logger.critical(f"Impossible de démarrer le scheduler : {e}")
        raise


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Arrête proprement le scheduler.

    Args:
        scheduler: Scheduler en cours d'exécution
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler arrêté proprement")
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du scheduler : {e}")
