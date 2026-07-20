"""
===============================================================================

Hermes OS

File:
market_intelligence.py

Purpose:
Immutable, validated domain models for the Market Intelligence framework.
Defines the standard report, regime, status, metadata, health, and context
types used by all Market Intelligence specialists.

This module is distinct from models/market_regime.py, which serves the
dedicated regime classification engine. The MarketRegime enum here is
scoped to the Market Intelligence framework and uses a different value set.

Author:
Hermes Quant Labs

Foundation:
VIII - Market Intelligence Framework

===============================================================================
"""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from json import dumps
from math import isfinite
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MarketRegime(str, Enum):
    """
    Market regime classifications used by Market Intelligence agents.

    These values are intentionally distinct from the regime engine's
    MarketRegime in models/market_regime.py. The intelligence framework
    uses coarser directional regime labels suited to advisory analysis.
    """

    STRONG_BULL_TREND = "STRONG_BULL_TREND"
    WEAK_BULL_TREND = "WEAK_BULL_TREND"
    RANGE_BOUND = "RANGE_BOUND"
    WEAK_BEAR_TREND = "WEAK_BEAR_TREND"
    STRONG_BEAR_TREND = "STRONG_BEAR_TREND"
    HIGH_VOLATILITY_TRANSITION = "HIGH_VOLATILITY_TRANSITION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AgentStatus(str, Enum):
    """Operational status of a Market Intelligence specialist."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    ERROR = "ERROR"
    DEGRADED = "DEGRADED"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _required(value: str, name: str) -> None:
    """Validate that a string value is non-empty."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")


def _bounded(
    value: float, name: str, low: float = 0.0, high: float = 1.0
) -> None:
    """Validate that a numeric value is finite and within [low, high]."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(
            f"{name} must be finite and between {low} and {high}."
        )


def utc(value: datetime, name: str) -> datetime:
    """Validate that a datetime is timezone-aware and return UTC-normalized."""
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-serializable form."""
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
    """Return deterministic JSON suitable for checksums and serialization."""
    return dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default stale-data threshold in seconds (24 hours).
STALE_THRESHOLD_SECONDS: int = 86400


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketIntelligenceContext:
    """
    Immutable base context for market intelligence analysis.

    Future specialist agents may extend or compose this type to carry
    specialist-specific validated inputs. The base context enforces
    required fields and UTC-aware timestamps.
    """

    symbol: str
    timeframe: str
    observed_at: datetime

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )


@dataclass(frozen=True)
class MarketIntelligenceReport:
    """
    Immutable, advisory-only report produced by Market Intelligence agents.

    This report contains no buy/sell actions, no order directives, and no
    portfolio mutations. It is purely explanatory evidence for human review.

    Fields:
        agent_name: Name of the producing specialist.
        symbol: Trading symbol analyzed.
        timeframe: Timeframe of the analysis.
        observed_at: UTC timestamp of the underlying observation.
        confidence: Normalized confidence in [0.0, 1.0].
        evidence: Tuple of supporting evidence strings.
        conflicting_evidence: Tuple of conflicting evidence strings.
        warnings: Tuple of warning strings.
        explanation: Human-readable explanation of the analysis.
        advisory_only: Always True; False is rejected.
    """

    agent_name: str
    symbol: str
    timeframe: str
    observed_at: datetime
    confidence: float
    evidence: tuple[str, ...]
    conflicting_evidence: tuple[str, ...]
    warnings: tuple[str, ...]
    explanation: str
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.agent_name, "agent_name")
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )
        _bounded(self.confidence, "confidence")
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be a tuple.")
        if not isinstance(self.conflicting_evidence, tuple):
            raise ValueError("conflicting_evidence must be a tuple.")
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be a tuple.")
        _required(self.explanation, "explanation")
        if not self.advisory_only:
            raise ValueError(
                "Market Intelligence reports must remain advisory-only."
            )

    @classmethod
    def create(
        cls,
        *,
        agent_name: str,
        symbol: str,
        timeframe: str,
        observed_at: datetime,
        confidence: float,
        evidence: tuple[str, ...],
        conflicting_evidence: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        explanation: str,
        now: datetime | None = None,
        stale_threshold_seconds: int = STALE_THRESHOLD_SECONDS,
    ) -> "MarketIntelligenceReport":
        """
        Create a validated report with future/stale timestamp handling.

        Future timestamps are rejected to prevent look-ahead bias.
        Stale timestamps are accepted with an appended warning so the
        observation remains usable but explicitly flagged.

        The injected ``now`` clock ensures deterministic validation in
        tests. When omitted, the current UTC time is used.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now = utc(now, "now")
        observed = utc(observed_at, "observed_at")

        if observed > now:
            raise ValueError("observed_at cannot be in the future.")

        age_seconds = (now - observed).total_seconds()
        extra_warnings: list[str] = []
        if age_seconds > stale_threshold_seconds:
            extra_warnings.append(
                f"Observation is stale: {int(age_seconds)} seconds old "
                f"(threshold: {stale_threshold_seconds})."
            )

        all_warnings = warnings + tuple(extra_warnings)
        return cls(
            agent_name=agent_name,
            symbol=symbol,
            timeframe=timeframe,
            observed_at=observed,
            confidence=confidence,
            evidence=evidence,
            conflicting_evidence=conflicting_evidence,
            warnings=all_warnings,
            explanation=explanation,
        )

    def to_dict(self) -> dict:
        """Return a deterministic dictionary representation."""
        return _jsonable(self)

    def to_json(self) -> str:
        """Return deterministic JSON serialization."""
        return stable_json(self)

    def checksum(self) -> str:
        """Return SHA-256 checksum of the deterministic JSON."""
        return sha256(self.to_json().encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Candle and specialist inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candle:
    """
    Immutable OHLCV candle for Market Intelligence analysis.

    Fields:
        timestamp: UTC-aware timestamp of the candle close.
        open: Opening price.
        high: Highest price.
        low: Lowest price.
        close: Closing price.
        volume: Trade volume.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "timestamp", utc(self.timestamp, "timestamp")
        )
        for field_name in ("open", "high", "low", "close", "volume"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            ):
                raise ValueError(f"{field_name} must be a finite number.")
        if not (self.low <= self.high):
            raise ValueError("low must be <= high.")
        if not (self.open <= self.high and self.open >= self.low):
            raise ValueError("open must be within [low, high].")
        if not (self.close <= self.high and self.close >= self.low):
            raise ValueError("close must be within [low, high].")
        if self.volume < 0:
            raise ValueError("volume must be non-negative.")


def _validate_candles(candles: tuple[Candle, ...]) -> None:
    """Validate that a tuple of candles is non-empty and ordered."""
    if not isinstance(candles, tuple):
        raise ValueError("candles must be a tuple.")
    if len(candles) == 0:
        raise ValueError("candles must not be empty.")
    for c in candles:
        if not isinstance(c, Candle):
            raise ValueError("candles must contain Candle instances.")
    for i in range(1, len(candles)):
        if candles[i].timestamp < candles[i - 1].timestamp:
            raise ValueError("candles must be in ascending timestamp order.")


@dataclass(frozen=True)
class TrendInputs:
    """
    Immutable inputs for the Trend Specialist.

    Fields:
        symbol: Trading symbol.
        timeframe: Timeframe label.
        observed_at: UTC-aware timestamp of the observation.
        candles: Tuple of validated candles in ascending time order.
    """

    symbol: str
    timeframe: str
    observed_at: datetime
    candles: tuple[Candle, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )
        _validate_candles(self.candles)


@dataclass(frozen=True)
class MomentumInputs:
    """
    Immutable inputs for the Momentum Specialist.

    Fields:
        symbol: Trading symbol.
        timeframe: Timeframe label.
        observed_at: UTC-aware timestamp of the observation.
        candles: Tuple of validated candles in ascending time order.
    """

    symbol: str
    timeframe: str
    observed_at: datetime
    candles: tuple[Candle, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )
        _validate_candles(self.candles)


@dataclass(frozen=True)
class VolumeInputs:
    """
    Immutable inputs for the Volume Specialist.

    Fields:
        symbol: Trading symbol.
        timeframe: Timeframe label.
        observed_at: UTC-aware timestamp of the observation.
        candles: Tuple of validated candles in ascending time order.
    """

    symbol: str
    timeframe: str
    observed_at: datetime
    candles: tuple[Candle, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )
        _validate_candles(self.candles)


@dataclass(frozen=True)
class VolatilityInputs:
    """
    Immutable inputs for the Volatility Specialist.

    Fields:
        symbol: Trading symbol.
        timeframe: Timeframe label.
        observed_at: UTC-aware timestamp of the observation.
        candles: Tuple of validated candles in ascending time order.
    """

    symbol: str
    timeframe: str
    observed_at: datetime
    candles: tuple[Candle, ...]

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        object.__setattr__(
            self, "observed_at", utc(self.observed_at, "observed_at")
        )
        _validate_candles(self.candles)


@dataclass(frozen=True)
class SpecialistMetadata:
    """
    Immutable metadata describing a Market Intelligence specialist.

    Fields:
        name: Human-readable specialist name.
        version: Semantic version of the specialist implementation.
        status: Current operational status.
        supported_symbols: Tuple of symbols the specialist can analyze.
        supported_timeframes: Tuple of timeframes the specialist can analyze.
        advisory_only: Always True; False is rejected.
    """

    name: str
    version: str
    status: AgentStatus
    supported_symbols: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.name, "name")
        _required(self.version, "version")
        if not isinstance(self.status, AgentStatus):
            raise ValueError("status must be an AgentStatus.")
        if not isinstance(self.supported_symbols, tuple):
            raise ValueError("supported_symbols must be a tuple.")
        if not isinstance(self.supported_timeframes, tuple):
            raise ValueError("supported_timeframes must be a tuple.")
        if not self.advisory_only:
            raise ValueError(
                "Market Intelligence specialists must remain advisory-only."
            )

    def to_dict(self) -> dict:
        """Return a deterministic dictionary representation."""
        return _jsonable(self)

    def to_json(self) -> str:
        """Return deterministic JSON serialization."""
        return stable_json(self)


@dataclass(frozen=True)
class HealthCheckResult:
    """
    Immutable health check result for a Market Intelligence specialist.

    Fields:
        agent_name: Name of the specialist checked.
        status: Operational status at check time.
        healthy: Whether the specialist is healthy.
        explanation: Human-readable explanation of the health state.
        checked_at: UTC timestamp of the check.
        advisory_only: Always True; False is rejected.
    """

    agent_name: str
    status: AgentStatus
    healthy: bool
    explanation: str
    checked_at: datetime
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.agent_name, "agent_name")
        if not isinstance(self.status, AgentStatus):
            raise ValueError("status must be an AgentStatus.")
        if not isinstance(self.healthy, bool):
            raise ValueError("healthy must be a boolean.")
        _required(self.explanation, "explanation")
        object.__setattr__(
            self, "checked_at", utc(self.checked_at, "checked_at")
        )
        if not self.advisory_only:
            raise ValueError(
                "Health check results must remain advisory-only."
            )

    def to_dict(self) -> dict:
        """Return a deterministic dictionary representation."""
        return _jsonable(self)

    def to_json(self) -> str:
        """Return deterministic JSON serialization."""
        return stable_json(self)
