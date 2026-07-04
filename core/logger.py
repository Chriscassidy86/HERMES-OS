"""
===============================================================================

Hermes OS

File:
logger.py

Purpose:
Central logging system for Hermes OS.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

import logging
from pathlib import Path
from core.config import config


def setup_logger(name: str = "hermes") -> logging.Logger:
    """
    Create and configure the Hermes logger.
    """

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file: Path = config.LOG_DIR / "hermes.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()