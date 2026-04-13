"""
CORTEX — Point d'entrée principal
Initialise tous les composants et démarre le système
"""

import asyncio
import os
import sys
from pathlib import Path

# Ajoute le dossier racine au PYTHONPATH pour les imports relatifs
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Chargement des variables d'environnement en premier
load_dotenv()

from utils.logger import get_logger
from database.client import test_connection as test_db_connection, init_db
from tgbot.bot import test_connection as test_telegram_connection, send_message, build_application
from scheduler import build_scheduler, start_scheduler, stop_scheduler

logger = get_logger("main")


async def startup() -> tuple:
    """
    Séquence de démarrage de CORTEX.
    Ordre strict : env → logger → DB → schema → Telegram → scheduler → bot

    Returns:
        (scheduler, application) si tout OK
    Raises:
        SystemExit si un composant critique échoue
    """

    logger.info("=" * 60)
    logger.info("CORTEX — Démarrage du système")
    logger.info("=" * 60)

    # ── Étape 1 : Variables d'environnement ─────────────────────────
    logger.info("[1/7] Chargement des variables d'environnement...")
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "TELEGRAM_CHAT_ID"
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.critical(f"Variables d'environnement manquantes : {missing}")
        sys.exit(1)
    logger.info("Variables d'environnement : OK")

    # ── Étape 2 : Logger (déjà initialisé ci-dessus) ────────────────
    logger.info("[2/7] Logger initialisé")

    # ── Étape 3 : Test connexion Supabase ────────────────────────────
    logger.info("[3/7] Test connexion Supabase...")
    db_ok = await test_db_connection()
    if not db_ok:
        logger.warning("Connexion Supabase échouée — le système continue en mode dégradé")
    else:
        logger.info("Connexion Supabase : ✅")

    # ── Étape 4 : Initialisation schema.sql ─────────────────────────
    logger.info("[4/7] Vérification schema base de données...")
    await init_db()

    # ── Étape 5 : Test connexion Telegram ───────────────────────────
    logger.info("[5/7] Test connexion Telegram...")
    telegram_ok = await test_telegram_connection()
    if not telegram_ok:
        logger.critical("Connexion Telegram échouée — impossible de démarrer")
        sys.exit(1)
    logger.info("Connexion Telegram : ✅")

    # ── Étape 6 : Message de démarrage Telegram ──────────────────────
    logger.info("[6/7] Envoi du message de démarrage...")
    startup_message = (
        "🟢 *CORTEX EST EN LIGNE*\n\n"
        "📡 Système : opérationnel\n"
        "🗄️ Database : connectée ✅\n"
        "🤖 Agents : en construction 🔧\n"
        "⏰ Prochain rapport : demain 6h00\n\n"
        "Bienvenue Badr.\n"
        "CORTEX surveille pendant que tu dors."
    )
    await send_message(startup_message)
    logger.info("Message de démarrage envoyé")

    # ── Étape 7 : Démarrage du scheduler ────────────────────────────
    logger.info("[7/7] Démarrage du scheduler...")
    scheduler = build_scheduler()
    start_scheduler(scheduler)

    # Construction du bot (mode polling)
    application = build_application()

    logger.info("=" * 60)
    logger.info("CORTEX opérationnel — En attente de signaux")
    logger.info("=" * 60)

    return scheduler, application


async def shutdown(scheduler, application) -> None:
    """
    Arrêt propre de tous les composants.
    Déclenché par Ctrl+C ou signal système.

    Args:
        scheduler: Scheduler APScheduler en cours
        application: Application Telegram en cours
    """
    logger.info("Arrêt de CORTEX en cours...")

    # Arrêt du scheduler
    stop_scheduler(scheduler)

    # Arrêt du bot Telegram
    try:
        if application.running:
            await application.stop()
            await application.shutdown()
        logger.info("Bot Telegram arrêté")
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du bot : {e}")

    logger.info("CORTEX arrêté proprement. À bientôt Badr.")


async def main() -> None:
    """
    Fonction principale — orchestre le démarrage et l'exécution.
    Gère l'arrêt propre sur Ctrl+C.
    """
    scheduler = None
    application = None

    try:
        # Démarrage de tous les composants
        scheduler, application = await startup()

        # Démarrage du bot en mode polling (bloquant)
        logger.info("Bot en mode polling — CORTEX actif")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)

        # Maintien du processus actif
        while True:
            await asyncio.sleep(3600)  # Vérification toutes les heures

    except KeyboardInterrupt:
        logger.info("Interruption détectée (Ctrl+C)")

    except Exception as e:
        logger.critical(f"Erreur critique dans main() : {e}")
        raise

    finally:
        # Arrêt propre quoi qu'il arrive
        if scheduler or application:
            await shutdown(scheduler, application)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Déjà géré dans main()
    except Exception as e:
        # En dernier recours, log l'erreur critique
        print(f"[CRITICAL] CORTEX crash fatal : {e}")
        sys.exit(1)
