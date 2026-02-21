"""
Spark Trend Analyzer - Plateforme d'analyse de tendances BigData
"""

from .api import app
from .agents import analyze_trend, KnoxLivyClient
from .models.config import Config
from .utils.logger import setup_logger
from .utils.serializers import make_json_serializable

__version__ = "1.0.0"

__all__ = [
    "app",
    "analyze_trend",
    "KnoxLivyClient",
    "Config",
    "setup_logger",
    "make_json_serializable"
]
__author__ = "Orange Sonatel"
__license__ = "Proprietary"
