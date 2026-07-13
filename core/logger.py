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
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from core.config import config


class JsonFormatter(logging.Formatter):
    def format(self,record):
        return json.dumps({"timestamp":self.formatTime(record),"level":record.levelname,"logger":record.name,"message":record.getMessage()},sort_keys=True)

def setup_logger(name: str = "hermes", max_bytes: int = 5_000_000, backup_count: int = 5) -> logging.Logger:
    """
    Create and configure the Hermes logger.
    """

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file: Path = config.LOG_DIR / "hermes.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    if logger.handlers:
        return logger

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
