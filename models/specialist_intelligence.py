"""Immutable validated inputs and outputs for V2 specialist intelligence."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LiquidityInputs:
    symbol: str
    bid_price: float
    ask_price: float
    bid_depth: float
    ask_depth: float
    observed_at: datetime


@dataclass(frozen=True)
class ProbabilityInputs:
    symbol: str
    supporting_signals: int
    opposing_signals: int
    neutral_signals: int
    mean_confidence: float
    observed_at: datetime


@dataclass(frozen=True)
class PortfolioContextInputs:
    symbol: str
    cash: float
    equity: float
    gross_exposure: float
    symbol_exposure: float
    open_positions: int
    observed_at: datetime


@dataclass(frozen=True)
class SpecialistAssessment:
    source: str
    symbol: str
    status: str
    score: float
    confidence: float
    facts: tuple[str, ...]
    warnings: tuple[str, ...]
    observed_at: datetime
    advisory_only: bool = True

