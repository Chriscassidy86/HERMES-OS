"""
===============================================================================

Hermes OS

File:
main.py

Purpose:
Primary entry point for Hermes OS.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from core.config import config
from core.logger import logger
from core.events import events
from core.orchestrator import orchestrator
from core.registry import registry


def on_system_boot(data):
    logger.info(f"System boot event received: {data}")


def main():
    events.subscribe("system.boot", on_system_boot)

    print("=" * 60)
    print(config.APP_NAME)
    print(config.COMPANY)
    print(config.VERSION)
    print(config.FOUNDATION)
    print("Status: STARTING")
    print("=" * 60)

    orchestrator.boot()

    print("=" * 60)
    print("Status: ONLINE")
    print("Registered components:", registry.list_items())
    print("=" * 60)


if __name__ == "__main__":
    main()