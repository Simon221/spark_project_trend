#!/usr/bin/env python3
"""
Point d'entrée principal pour l'application Spark Trend Analyzer
"""

import uvicorn
import logging
import sys
from pathlib import Path

# Ajouter le répertoire racine au chemin
sys.path.insert(0, str(Path(__file__).parent))

from src.api.server import app
from src.models.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Lancer l'application"""
    
    logger.info("=" * 60)
    logger.info("Démarrage de Spark Trend Analyzer")
    logger.info("=" * 60)
    
    # Afficher la configuration
    logger.info(f"Knox Host: {Config.KNOX_HOST}")
    logger.info(f"LLM Model: {Config.LLM_MODEL}")
    logger.info(f"Spark Driver Memory: {Config.DRIVER_MEMORY}")
    logger.info(f"Spark Executors: {Config.NUM_EXECUTORS}")
    
    # Lancer uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
