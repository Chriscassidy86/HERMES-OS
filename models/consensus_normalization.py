"""Immutable output of deterministic market-consensus normalization."""

from dataclasses import dataclass
from datetime import datetime

from models.market_consensus import ConsensusConflict, ConsensusContribution, ConsensusDirection, _bounded, _finite, _required, utc


@dataclass(frozen=True)
class ConsensusNormalization:
    symbol: str
    timeframe: str
    evaluated_at: datetime
    direction: ConsensusDirection
    score: float
    confidence: float
    uncertainty: float
    source_count: int
    independent_source_count: int
    category_count: int
    contributions: tuple[ConsensusContribution, ...]
    bullish_contributions: tuple[str, ...]
    bearish_contributions: tuple[str, ...]
    neutral_contributions: tuple[str, ...]
    excluded_observations: tuple[tuple[str, str], ...]
    conflicts: tuple[ConsensusConflict, ...]
    crowding_warning: str | None
    concentration_warning: str | None
    freshness_warning: str | None
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        utc(self.evaluated_at, "evaluated_at")
        _finite(self.score, "score", -1.0, 1.0)
        _bounded(self.confidence, "confidence")
        _bounded(self.uncertainty, "uncertainty")
        if min(self.source_count, self.independent_source_count, self.category_count) < 0:
            raise ValueError("Normalization counts cannot be negative.")
