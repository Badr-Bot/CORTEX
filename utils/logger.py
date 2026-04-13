"""
CORTEX — Module de logging structuré
Gère les logs console + fichier avec rotation quotidienne
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logger(name: str) -> logging.Logger:
    """
    Crée et configure un logger structuré pour un module donné.

    Format : [TIMESTAMP] [LEVEL] [MODULE] message
    Sortie : console + fichier logs/cortex.log
    Rotation : nouveau fichier chaque jour, garde 30 jours

    Args:
        name: Nom du module (ex: 'database', 'telegram', 'scheduler')

    Returns:
        logging.Logger configuré
    """

    # Création du dossier logs s'il n'existe pas
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Format des messages de log
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Création du logger
    logger = logging.getLogger(f"cortex.{name}")
    logger.setLevel(logging.DEBUG)

    # Évite les doublons si le logger existe déjà
    if logger.handlers:
        return logger

    # Handler console — niveau INFO et au-dessus
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Handler fichier avec rotation quotidienne
    log_file = logs_dir / "cortex.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",          # Rotation à minuit
        interval=1,               # Chaque jour
        backupCount=30,           # Garde 30 jours d'historique
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Tout dans les fichiers
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"      # Suffix de rotation : cortex.log.2024-01-15

    # Ajout des handlers au logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Logger global CORTEX (racine)
def get_logger(module: str) -> logging.Logger:
    """
    Point d'entrée unique pour obtenir un logger dans n'importe quel module.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Message d'information")
        logger.warning("Anomalie non critique")
        logger.error("Erreur catchée")
        logger.critical("Erreur nécessitant attention")
    """
    return setup_logger(module)


# Niveaux de log disponibles :
# logger.info("INFO : opération normale")
# logger.warning("WARNING : anomalie non critique")
# logger.error("ERROR : erreur catchée")
# logger.critical("CRITICAL : erreur qui nécessite attention")
