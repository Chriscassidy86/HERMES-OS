"""Immutable multi-timeframe specialist and alignment explanations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimeframeView:
    timeframe: str
    direction: str
    confidence: float
    evidence: tuple[str, ...]
    timestamp: datetime


@dataclass(frozen=True)
class HorizonExplanation:
    horizon: str
    direction: str
    confidence: float
    timeframes: tuple[str, ...]
    evidence: tuple[str, ...]
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class SpecialistTimeframeExplanation:
    source: str
    short_term: HorizonExplanation
    medium_term: HorizonExplanation
    long_term: HorizonExplanation
    aligned_direction: str
    conflicts: tuple[str, ...]


@dataclass(frozen=True)
class MultiTimeframeSummary:
    symbol: str
    specialists: tuple[SpecialistTimeframeExplanation, ...]
    aligned_direction: str
    confidence: float
    alignment: tuple[str, ...]
    conflicts: tuple[str, ...]
    assumptions: tuple[str, ...]
    as_of: datetime

