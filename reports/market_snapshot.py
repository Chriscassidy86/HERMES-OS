"""
===============================================================================

Hermes OS

File:
market_snapshot.py

Purpose:
Stores the current market snapshot shared by all agents.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class MarketSnapshot:
    """
    Represents the overall market at one point in time.
    """

    symbol: str
    price: float
    volume_24h: float
    market_trend: str
    volatility: float
    fear_greed_index: int

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def summary(self) -> str:
        return (
            f"{self.symbol} | "
            f"Price ${self.price:,.2f} | "
            f"Trend: {self.market_trend} | "
            f"Fear & Greed: {self.fear_greed_index}"
        )