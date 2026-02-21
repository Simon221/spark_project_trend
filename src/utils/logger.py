"""
Logging Configuration
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path


# Créer un dossier logs centralisé
LOG_DIR = Path("/tmp/spark_trend_logs")
LOG_DIR.mkdir(exist_ok=True)

# Fichier de log unique pour toute l'app
MAIN_LOG_FILE = LOG_DIR / "app.log"


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Setup et configure un logger
    
    Args:
        name: Nom du logger
        level: Niveau de logging
        
    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Éviter les handlers dupliqués
    if logger.handlers:
        return logger
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler - utiliser un seul fichier centralisé
    try:
        file_handler = logging.FileHandler(MAIN_LOG_FILE)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")
    
    return logger


# Logger global
logger = setup_logger("spark_trend", logging.INFO)

__all__ = ["setup_logger", "logger"]
