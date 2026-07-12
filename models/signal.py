"""
===============================================================================

Hermes OS

File:
signal.py

Purpose:
Represents a machine-readable trading signal produced by a specialist.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Signal:
    """
    A standardized signal produced by a specialist.

    Unlike AgentReport, this object is intended for Hermes itself
    and will be consumed by the Decision Engine.
    """

    source: str
    direction: str
    confidence: float
    strength: float
    timeframe: str
    priority: int
    timestamp: datetime = datetime.now(timezone.utc)
    evidence: tuple[str, ...] = ()

    def summary(self) -> str:
        return (
            f"{self.source} | "
            f"{self.direction} | "
            f"Confidence: {self.confidence:.1f}% | "
            f"Strength: {self.strength:.2f} | "
            f"Timeframe: {self.timeframe}"
        )
