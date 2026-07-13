"""
===============================================================================

Hermes OS

File:
config.py

Purpose:
Central configuration management for Hermes OS.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HermesConfig:
    """
    Global configuration for Hermes OS.
    """

    APP_NAME: str = "Hermes OS"
    COMPANY: str = "Hermes Quant Labs"
    VERSION: str = "0.1.0"
    FOUNDATION: str = "Foundation II - The Nervous System"

    ROOT_DIR: Path = Path(__file__).resolve().parent.parent

    LOG_DIR: Path = ROOT_DIR / "logs"
    DATA_DIR: Path = ROOT_DIR / "data"
    DATABASE_DIR: Path = ROOT_DIR / "database"

    PAPER_TRADING: bool = True
    LIVE_TRADING: bool = False

    DEBUG: bool = True


config = HermesConfig()
