"""Immutable, validated domain models for advisory market consensus evidence."""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from json import dumps
from math import isfinite
from typing import Any


class ConsensusDirection(str, Enum):
    STRONG_BEARISH = "STRONG_BEARISH"
    BEARISH = "BEARISH"
    LEAN_BEARISH = "LEAN_BEARISH"
    NEUTRAL = "NEUTRAL"
    LEAN_BULLISH = "LEAN_BULLISH"
    BULLISH = "BULLISH"
    STRONG_BULLISH = "STRONG_BULLISH"
    UNKNOWN = "UNKNOWN"


class SourceCategory(str, Enum):
    TECHNICAL_CONSENSUS = "TECHNICAL_CONSENSUS"
    DERIVATIVES = "DERIVATIVES"
    SENTIMENT = "SENTIMENT"
    ON_CHAIN = "ON_CHAIN"
    MARKET_BREADTH = "MARKET_BREADTH"
    NEWS = "NEWS"
    ANALYST_COMMUNITY = "ANALYST_COMMUNITY"
    MACRO = "MACRO"
    PUBLIC_EXCHANGE_METRICS = "PUBLIC_EXCHANGE_METRICS"


class ConsensusState(str, Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    MODERATELY_BULLISH = "MODERATELY_BULLISH"
    SLIGHTLY_BULLISH = "SLIGHTLY_BULLISH"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_BEARISH = "SLIGHTLY_BEARISH"
    MODERATELY_BEARISH = "MODERATELY_BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNTRUSTED_DATA = "UNTRUSTED_DATA"


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")


def _bounded(value: float, name: str, low: float = 0.0, high: float = 1.0) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and between {low} and {high}.")


def _finite(value: float, name: str, low: float | None = None, high: float | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{name} is outside the permitted range.")


def utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, datetime):
        return utc(value, "timestamp").isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def stable_json(value: Any) -> str:
    """Return deterministic JSON suitable for checksums and SQLite payloads."""
    return dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class ConsensusSource:
    source_id: str
    display_name: str
    category: SourceCategory
    default_reliability: float
    trust_level: str
    data_label: str
    provenance: str
    enabled: bool
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required(self.source_id, "source_id")
        _required(self.display_name, "display_name")
        if not isinstance(self.category, SourceCategory):
            raise ValueError("category must be a SourceCategory.")
        _bounded(self.default_reliability, "default_reliability")
        _required(self.trust_level, "trust_level")
        if self.data_label not in {"PUBLIC", "FIXTURE", "EXPORT", "LICENSED", "UNAVAILABLE"}:
            raise ValueError("data_label is not governed.")
        _required(self.provenance, "provenance")


@dataclass(frozen=True)
class ConsensusSignal:
    direction: ConsensusDirection
    score: float
    confidence: float
    strength: float
    uncertainty: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.direction, ConsensusDirection):
            raise ValueError("direction must be a ConsensusDirection.")
        _finite(self.score, "score", -1.0, 1.0)
        _bounded(self.confidence, "confidence")
        _bounded(self.strength, "strength")
        if self.direction is ConsensusDirection.UNKNOWN and self.score != 0:
            raise ValueError("UNKNOWN direction must have a zero score.")


@dataclass(frozen=True)
class ConsensusObservation:
    schema_version: int
    observation_id: str
    source_id: str
    source_name: str
    source_category: SourceCategory
    symbol: str
    timeframe: str
    observed_at: datetime
    ingested_at: datetime
    freshness_seconds: int
    raw_value: str | float | None
    signal: ConsensusSignal
    source_reliability: float
    trust_level: str
    provenance: str
    data_label: str
    reference: str | None
    checksum: str
    limitations: tuple[str, ...]
    warnings: tuple[str, ...]
    eligible_for_consensus: bool
    exclusion_reason: str | None
    underlying_dataset: str

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported consensus observation schema.")
        for value, name in ((self.observation_id, "observation_id"), (self.source_id, "source_id"), (self.source_name, "source_name"), (self.symbol, "symbol"), (self.timeframe, "timeframe"), (self.trust_level, "trust_level"), (self.provenance, "provenance"), (self.underlying_dataset, "underlying_dataset")):
            _required(value, name)
        if not isinstance(self.source_category, SourceCategory):
            raise ValueError("source_category must be a SourceCategory.")
        observed = utc(self.observed_at, "observed_at")
        ingested = utc(self.ingested_at, "ingested_at")
        if observed > ingested.replace(microsecond=0) and (observed - ingested).total_seconds() > 60:
            raise ValueError("Future consensus observations are rejected.")
        if self.freshness_seconds < 0:
            raise ValueError("freshness_seconds cannot be negative.")
        if isinstance(self.raw_value, float):
            _finite(self.raw_value, "raw_value")
        _bounded(self.source_reliability, "source_reliability")
        if self.data_label not in {"PUBLIC", "FIXTURE", "EXPORT", "LICENSED"}:
            raise ValueError("Observation data_label is not allowed.")
        _required(self.checksum, "checksum")
        if self.eligible_for_consensus and self.exclusion_reason:
            raise ValueError("Eligible observations cannot have an exclusion reason.")
        if not self.eligible_for_consensus and not self.exclusion_reason:
            raise ValueError("Ineligible observations require an exclusion reason.")

    @classmethod
    def create(cls, *, observation_id: str, source: ConsensusSource, symbol: str, timeframe: str, observed_at: datetime, ingested_at: datetime, raw_value: str | float | None, signal: ConsensusSignal, reference: str | None = None, limitations: tuple[str, ...] = (), warnings: tuple[str, ...] = (), eligible_for_consensus: bool = True, exclusion_reason: str | None = None, underlying_dataset: str | None = None) -> "ConsensusObservation":
        observed = utc(observed_at, "observed_at")
        ingested = utc(ingested_at, "ingested_at")
        freshness = max(0, int((ingested - observed).total_seconds()))
        payload = (observation_id, source.source_id, symbol, timeframe, observed.isoformat(), raw_value, signal.direction.value, signal.score, signal.confidence, source.provenance)
        checksum = sha256(stable_json(payload).encode("utf-8")).hexdigest()
        return cls(1, observation_id, source.source_id, source.display_name, source.category, symbol, timeframe, observed, ingested, freshness, raw_value, signal, source.default_reliability, source.trust_level, source.provenance, source.data_label, reference, checksum, limitations or source.limitations, warnings, eligible_for_consensus, exclusion_reason, underlying_dataset or source.source_id)


@dataclass(frozen=True)
class ConsensusContribution:
    observation_id: str
    source_id: str
    category: SourceCategory
    direction: ConsensusDirection
    raw_score: float
    adjusted_score: float
    weight: float
    independent: bool
    explanation: str

    def __post_init__(self) -> None:
        _required(self.observation_id, "observation_id")
        _required(self.source_id, "source_id")
        _finite(self.raw_score, "raw_score", -1.0, 1.0)
        _finite(self.adjusted_score, "adjusted_score", -1.0, 1.0)
        _bounded(self.weight, "weight")
        _required(self.explanation, "explanation")


@dataclass(frozen=True)
class ConsensusAgreement:
    state: str
    source_ids: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class ConsensusConflict:
    source_ids: tuple[str, ...]
    severity: float
    explanation: str

    def __post_init__(self) -> None:
        _bounded(self.severity, "severity")
        if len(self.source_ids) < 2:
            raise ValueError("A conflict requires at least two sources.")


@dataclass(frozen=True)
class ConsensusSnapshot:
    schema_version: int
    symbol: str
    timeframe: str
    evaluated_at: datetime
    observations: tuple[ConsensusObservation, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        utc(self.evaluated_at, "evaluated_at")
        ids = tuple(item.observation_id for item in self.observations)
        if len(ids) != len(set(ids)):
            raise ValueError("Consensus snapshots cannot contain duplicate observation IDs.")
        if self.observations != tuple(sorted(self.observations, key=lambda item: (item.source_id, item.observed_at, item.observation_id))):
            raise ValueError("Consensus observations must use deterministic ordering.")

    @classmethod
    def build(cls, symbol: str, timeframe: str, evaluated_at: datetime, observations: tuple[ConsensusObservation, ...]) -> "ConsensusSnapshot":
        unique: dict[str, ConsensusObservation] = {}
        for item in observations:
            existing = unique.get(item.observation_id)
            if existing and existing.checksum != item.checksum:
                raise ValueError("Conflicting duplicate consensus observation.")
            unique[item.observation_id] = item
        ordered = tuple(sorted(unique.values(), key=lambda item: (item.source_id, item.observed_at, item.observation_id)))
        return cls(1, symbol, timeframe, utc(evaluated_at, "evaluated_at"), ordered)


@dataclass(frozen=True)
class ConsensusAssessment:
    assessment_id: str
    symbol: str
    timeframe: str
    evaluated_at: datetime
    state: ConsensusState
    score: float
    confidence: float
    uncertainty: float
    contributions: tuple[ConsensusContribution, ...]
    conflicts: tuple[ConsensusConflict, ...]
    excluded_observation_ids: tuple[str, ...]
    explanation: str
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.assessment_id, "assessment_id")
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        utc(self.evaluated_at, "evaluated_at")
        _finite(self.score, "score", -1.0, 1.0)
        _bounded(self.confidence, "confidence")
        _bounded(self.uncertainty, "uncertainty")
        if not self.advisory_only:
            raise ValueError("Market consensus assessments must remain advisory.")


@dataclass(frozen=True)
class ConsensusOutcome:
    observation_id: str
    source_id: str
    horizon_seconds: int
    classification: str
    evaluated_at: datetime
    favorable_movement: float
    adverse_movement: float
    explanation: str

    def __post_init__(self) -> None:
        if self.horizon_seconds <= 0:
            raise ValueError("Outcome horizon must be positive.")
        utc(self.evaluated_at, "evaluated_at")
        _finite(self.favorable_movement, "favorable_movement")
        _finite(self.adverse_movement, "adverse_movement")


@dataclass(frozen=True)
class SourcePerformance:
    source_id: str
    eligible_observations: int
    resolved_observations: int
    correct_observations: int
    incorrect_observations: int
    accuracy: float | None
    calibration: float | None
    sample_warning: str | None
    recommendations: tuple[str, ...]
    last_evaluated_at: datetime | None
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.source_id, "source_id")
        for value in (self.eligible_observations, self.resolved_observations, self.correct_observations, self.incorrect_observations):
            if value < 0:
                raise ValueError("Source performance counts cannot be negative.")
        if self.accuracy is not None:
            _bounded(self.accuracy, "accuracy")
        if self.calibration is not None:
            _bounded(self.calibration, "calibration")
        if self.last_evaluated_at is not None:
            utc(self.last_evaluated_at, "last_evaluated_at")
        if not self.advisory_only:
            raise ValueError("Source performance cannot mutate configuration.")


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    observed_at: datetime
    status: str
    latency_ms: float | None
    consecutive_failures: int
    rate_limited: bool
    explanation: str

    def __post_init__(self) -> None:
        _required(self.source_id, "source_id")
        utc(self.observed_at, "observed_at")
        _required(self.status, "status")
        if self.latency_ms is not None:
            _finite(self.latency_ms, "latency_ms", 0)
        if self.consecutive_failures < 0:
            raise ValueError("consecutive_failures cannot be negative.")
