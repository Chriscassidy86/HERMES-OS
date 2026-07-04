"""
===============================================================================

Hermes OS

File:
orchestrator.py

Purpose:
Coordinates Hermes OS startup and core systems.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from core.config import config
from core.logger import logger
from core.events import events
from core.registry import registry
from core.scheduler import scheduler


class Orchestrator:
    """Coordinates Hermes OS."""

    def boot(self) -> None:
        """Boot Hermes OS."""

        logger.info("Booting Hermes OS...")

        registry.register("config", config)
        registry.register("logger", logger)
        registry.register("event_bus", events)
        registry.register("scheduler", scheduler)

        events.publish("system.boot", {
            "app": config.APP_NAME,
            "version": config.VERSION,
            "foundation": config.FOUNDATION,
            "status": "ONLINE",
        })

        logger.info("Hermes OS boot complete.")


orchestrator = Orchestrator()
