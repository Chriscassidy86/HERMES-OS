"""
===============================================================================

Hermes OS

File:
registry.py

Purpose:
Central registry for Hermes components, agents, services, and strategies.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from typing import Any, Dict

from core.logger import logger


class Registry:
    """
    Stores named components so Hermes can find them without hard-coding dependencies.
    """

    def __init__(self):
        self._items: Dict[str, Any] = {}

    def register(self, name: str, item: Any):
        """Register a component by name."""
        if name in self._items:
            logger.warning(f"Registry item overwritten: {name}")

        self._items[name] = item
        logger.info(f"Registered component: {name}")

    def get(self, name: str) -> Any:
        """Retrieve a registered component by name."""
        return self._items.get(name)

    def list_items(self):
        """Return all registered component names."""
        return list(self._items.keys())


registry = Registry()
