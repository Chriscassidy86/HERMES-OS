"""
===============================================================================

Hermes OS

File:
decision_packet.py

Purpose:
Collects specialist signals before the Decision Engine evaluates them.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.signal import Signal


@dataclass(frozen=True)
class DecisionPacket:
    """
    A collection of signals submitted by Hermes specialists.
    """

    symbol: str
    signals: tuple[Signal, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_signal(self, signal: Signal) -> "DecisionPacket":
        """
        Return a new DecisionPacket with one additional signal.
        """

        return DecisionPacket(
            symbol=self.symbol,
            signals=(*self.signals, signal),
            created_at=self.created_at,
        )

    def signal_count(self) -> int:
        """
        Return the number of signals in the packet.
        """

        return len(self.signals)

    def summary(self) -> str:
        """
        Return a readable packet summary.
        """

        return f"{self.symbol} DecisionPacket | Signals: {self.signal_count()}"
