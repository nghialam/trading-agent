"""
Helper Utilities for the Trading Agent
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
    
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}


def validate_symbol(symbol: str) -> bool:
    if not symbol or len(symbol) > 10:
        return False
    
    return symbol.isalpha()


def format_signal_log(signal) -> str:
    return (
        f"[{signal.timestamp}] {signal.action} {signal.symbol} "
        f"(Confidence: {signal.confidence:.2%})"
     )


def ensure_directory(path: str) -> Path:
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


class ConfigurableStrategy:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def get_param(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
    
    def has_param(self, key: str) -> bool:
        return key in self.config
