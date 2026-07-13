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

    previous_price: float | None = None
    average_volume: float | None = None
    short_moving_average: float | None = None
    long_moving_average: float | None = None
    timeframe: str = "4H"

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = "UNSPECIFIED"
    source_timestamp: datetime | None = None

    def summary(self) -> str:
        return (
            f"{self.symbol} | "
            f"Price ${self.price:,.2f} | "
            f"Trend: {self.market_trend} | "
            f"Fear & Greed: {self.fear_greed_index}"
        )
