"""
Configuration Module
Centralise toutes les variables de configuration
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()


class Config:
    """Configuration centralisée"""
    
    # ========================================
    # Knox Gateway Configuration
    # ========================================
    KNOX_HOST = os.getenv("KNOX_HOST", "mespmasterprd3.orange-sonatel.com:8443")
    AD_USER = os.getenv("AD_USER", "sddesigner")
    AD_PASSWORD = os.getenv("AD_PASSWORD", "")
    
    # ========================================
    # Spark Configuration
    # ========================================
    DRIVER_MEMORY = os.getenv("DRIVER_MEMORY", "4g")
    DRIVER_CORES = int(os.getenv("DRIVER_CORES", "2"))
    EXECUTOR_MEMORY = os.getenv("EXECUTOR_MEMORY", "4g")
    EXECUTOR_CORES = int(os.getenv("EXECUTOR_CORES", "2"))
    NUM_EXECUTORS = int(os.getenv("NUM_EXECUTORS", "4"))
    QUEUE = os.getenv("QUEUE", "root.datalake")
    
    # ========================================
    # Recovery JAR Configuration
    # ========================================
    RECOVERY_JAR_PATH = os.getenv("RECOVERY_JAR_PATH", "hdfs://path/to/recovery.jar")
    RECOVERY_JAR_CLASS = os.getenv("RECOVERY_JAR_CLASS", "com.orange.Recovery")
    
    # ========================================
    # LLM Configuration (OpenAI GPT-4o)
    # ========================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
    
    # ========================================
    # Trend Analysis Thresholds
    # ========================================
    TREND_THRESHOLDS = {
        "volume": {"warning": -0.10, "critical": -0.25},
        "quality": {"warning": 0.05, "critical": 0.15}
    }
    
    # ========================================
    # Available Tables & Schemas
    # ========================================
    TABLE_SCHEMAS = {
        "splio.active": {
            "columns": ["msisdn", "date_event", "top_active", "year", "month", "day"],
            "metrics": ["COUNT(msisdn)", "sum(top_active)"]
        },
        "splio.subscription": {
            "columns": ["msisdn", "date_subs", "subscription_name", "cnt_bund", "rev_bund", "year", "month", "day"],
            "metrics": ["COUNT(msisdn)", "COUNT(DISTINCT subscription_name)", "sum(cnt_bund)", "sum(rev_bund)"]
        }
    }


# Aliases pour compatibilité
__all__ = ["Config"]
