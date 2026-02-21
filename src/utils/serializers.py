"""
JSON Serialization Utilities
"""

from datetime import datetime
from typing import Any


def make_json_serializable(obj: Any) -> Any:
    """
    Convertir les objets en JSON sérialisables
    
    Gère:
    - datetime objects
    - dict (récursif)
    - list/tuple (récursif)
    - objets avec __dict__
    
    Args:
        obj: Objet à sérialiser
        
    Returns:
        Objet sérialisable en JSON
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return make_json_serializable(obj.__dict__)
    else:
        return obj


__all__ = ["make_json_serializable"]
