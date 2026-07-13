"""
===============================================================================

Hermes OS

File:
events.py

Purpose:
Simple event system used for communication between Hermes components.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from collections import defaultdict
from typing import Callable, Dict, List, Any

from core.logger import logger


class EventBus:
    """
    Simple publish/subscribe event system.
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable):
        """Register a callback for an event."""
        self._listeners[event_name].append(callback)
        logger.info(f"Subscribed to event: {event_name}")

    def publish(self, event_name: str, data: Any = None):
        """Publish an event to all listeners."""
        logger.info(f"Publishing event: {event_name}")

        for callback in self._listeners[event_name]:
            callback(data)


events = EventBus()
