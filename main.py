"""
CORTEX — Point d'entrée principal
Initialise tous les composants et démarre le système
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from utils.logger import get_logger
from database.client import test_connection as test_db_connection
from tgbot.bot import test_connection as test_telegram_connection, send_message, build_application
from scheduler import build_scheduler, start_scheduler, stop_scheduler

logger = get_logger("main")


async def startup() -> tuple:
    logger.info("=" * 60)
    logger.info("CORTEX — Démarrage du système")
    logger.info("=" * 60)

    # ── Étape 1 : Variables d'environnement ─────────────────────────
    logger.info("[1/5] Chargement des variables d'environnement...")
    telegram_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    supabase_enabled = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))
    logger.info(
        f"Variables OK (Telegram {'on' if telegram_enabled else 'off'}, "
        f"Supabase {'on' if supabase_enabled else 'off'})"
    )

    # ── Étape 2 : Test connexion Supabase (optionnel) ────────────────
    logger.info("[2/5] Test connexion Supabase...")
    if supabase_enabled:
        db_ok = await test_db_connection()
        logger.info(f"Supabase : {'OK' if db_ok else 'ECHEC (dashboard desactive)'}")
    else:
        logger.info("Supabase desactive")

    # ── Étape 3 : Test connexion Telegram ───────────────────────────
    application = None
    if telegram_enabled:
        logger.info("[3/5] Test connexion Telegram...")
        telegram_ok = await test_telegram_connection()
        if telegram_ok:
            logger.info("Telegram : OK")
            logger.info("[4/5] Message de demarrage...")
            await send_message("Systeme redemarre. Prochain rapport demain a 6h.")
            application = build_application()
        else:
            logger.warning("Telegram echec — mode degrade")
    else:
        logger.info("[3/5] Telegram desactive")

    # ── Étape 5 : Scheduler ──────────────────────────────────────────
    logger.info("[5/5] Demarrage du scheduler...")
    scheduler = build_scheduler()
    start_scheduler(scheduler)

    logger.info("=" * 60)
    logger.info("CORTEX operationnel")
    logger.info("=" * 60)

    return scheduler, application


async def shutdown(scheduler, application) -> None:
    logger.info("Arret de CORTEX en cours...")
    stop_scheduler(scheduler)
    if application is not None:
        try:
            if application.running:
                await application.stop()
                await application.shutdown()
            logger.info("Bot Telegram arrete")
        except Exception as e:
            logger.error(f"Erreur arret bot : {e}")
    logger.info("CORTEX arrete proprement.")


async def main() -> None:
    scheduler = None
    application = None
    try:
        scheduler, application = await startup()
        if application is not None:
            await application.initialize()
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Interruption (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Erreur critique : {e}")
        raise
    finally:
        if scheduler or application:
            await shutdown(scheduler, application)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[CRITICAL] CORTEX crash : {e}")
        sys.exit(1)
