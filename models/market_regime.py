"""Immutable inputs and output for deterministic market-regime research."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MarketRegime(str, Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    SIDEWAYS = "SIDEWAYS"
    ACCUMULATION = "ACCUMULATION"
    DISTRIBUTION = "DISTRIBUTION"
    BREAKOUT = "BREAKOUT"
    BREAKDOWN = "BREAKDOWN"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    TRANSITION = "TRANSITION"


@dataclass(frozen=True)
class RegimeInputs:
    symbol: str
    price: float
    previous_price: float
    short_moving_average: float
    long_moving_average: float
    volume: float
    average_volume: float
    volatility: float
    baseline_volatility: float
    reference_high: float
    reference_low: float
    buy_volume_ratio: float
    observed_at: datetime


@dataclass(frozen=True)
class RegimeClassification:
    symbol: str
    regime: MarketRegime
    confidence: float
    evidence: tuple[str, ...]
    explanation: str
    uncertainty: tuple[str, ...]
    observed_at: datetime
    advisory_only: bool = True


class InsufficientRegimeEvidence(ValueError):
    """Raised when validated evidence cannot support a regime classification."""

