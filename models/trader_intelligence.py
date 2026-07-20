"""Immutable, validated domain models for advisory trader intelligence.

Trader ideas are advisory evidence only. They cannot enter the DecisionPacket,
Risk Manager, execution, portfolio, or consensus boundaries. ENTER_SHORT_ADVISORY
is information only and must never open a short position or create an executable
order.
"""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from json import dumps
from math import isfinite
from typing import Any


class TraderThesisDirection(str, Enum):
    """Supported directional thesis values for trader ideas."""

    STRONG_BEARISH = "STRONG_BEARISH"
    BEARISH = "BEARISH"
    LEAN_BEARISH = "LEAN_BEARISH"
    NEUTRAL = "NEUTRAL"
    LEAN_BULLISH = "LEAN_BULLISH"
    BULLISH = "BULLISH"
    STRONG_BULLISH = "STRONG_BULLISH"
    UNKNOWN = "UNKNOWN"


class TraderSuggestedAction(str, Enum):
    """Supported suggested actions for trader ideas.

    ENTER_SHORT_ADVISORY is information only. It must never open a short
    position or create an executable order.
    """

    ENTER_LONG = "ENTER_LONG"
    EXIT_LONG = "EXIT_LONG"
    ENTER_SHORT_ADVISORY = "ENTER_SHORT_ADVISORY"
    EXIT_SHORT_ADVISORY = "EXIT_SHORT_ADVISORY"
    HOLD = "HOLD"
    WAIT = "WAIT"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    INCREASE_EXPOSURE_ADVISORY = "INCREASE_EXPOSURE_ADVISORY"
    UNKNOWN = "UNKNOWN"


class TraderSourceType(str, Enum):
    """Supported source types for trader idea provenance."""

    MANUAL = "MANUAL"
    JSON_IMPORT = "JSON_IMPORT"
    CSV_IMPORT = "CSV_IMPORT"
    FIXTURE = "FIXTURE"


class TraderEvaluationStatus(str, Enum):
    """Evaluation status for trader ideas."""

    PENDING = "PENDING"
    RESOLVED_CORRECT = "RESOLVED_CORRECT"
    RESOLVED_INCORRECT = "RESOLVED_INCORRECT"
    RESOLVED_INCONCLUSIVE = "RESOLVED_INCONCLUSIVE"
    EXPIRED = "EXPIRED"


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


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat()
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


def stable_checksum(value: Any) -> str:
    """Return a SHA-256 checksum over the stable JSON of value."""
    return sha256(stable_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TraderSource:
    """A governed source for trader ideas (manual, import, or fixture)."""

    source_id: str
    source_name: str
    source_type: TraderSourceType
    source_reference: str | None
    trust_level: str
    provenance: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required(self.source_id, "source_id")
        _required(self.source_name, "source_name")
        if not isinstance(self.source_type, TraderSourceType):
            raise ValueError("source_type must be a TraderSourceType.")
        _required(self.trust_level, "trust_level")
        _required(self.provenance, "provenance")


@dataclass(frozen=True)
class TraderProfile:
    """A trader's display identity and attribution metadata."""

    trader_id: str
    display_name: str
    attribution: str
    known_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required(self.trader_id, "trader_id")
        _required(self.display_name, "display_name")
        _required(self.attribution, "attribution")


@dataclass(frozen=True)
class TraderMarketContext:
    """Market conditions at the time a trader idea was published."""

    symbol: str
    timeframe: str
    market_regime: str

    def __post_init__(self) -> None:
        _required(self.symbol, "symbol")
        _required(self.timeframe, "timeframe")
        _required(self.market_regime, "market_regime")


@dataclass(frozen=True)
class TraderTradePlan:
    """Stated entry, stop, and target levels from a trader idea.

    All fields are optional because traders do not always state exact levels.
    """

    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    target_prices: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("entry_zone_low", self.entry_zone_low),
            ("entry_zone_high", self.entry_zone_high),
            ("stop_loss", self.stop_loss),
        ):
            if value is not None:
                _finite(value, name, 0.0)
        for target in self.target_prices:
            _finite(target, "target_price", 0.0)
        if (
            self.entry_zone_low is not None
            and self.entry_zone_high is not None
            and self.entry_zone_high < self.entry_zone_low
        ):
            raise ValueError("entry_zone_high cannot be below entry_zone_low.")


@dataclass(frozen=True)
class TraderThesis:
    """The directional thesis and explanation from a trader idea."""

    direction: TraderThesisDirection
    stated_confidence: float | None
    explanation: str
    supporting_evidence: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.direction, TraderThesisDirection):
            raise ValueError("direction must be a TraderThesisDirection.")
        if self.stated_confidence is not None:
            _bounded(self.stated_confidence, "stated_confidence")
        _required(self.explanation, "explanation")


@dataclass(frozen=True)
class TraderIdeaRecord:
    """An immutable, validated trader idea record.

    Trader ideas are advisory evidence only. They cannot enter the
    DecisionPacket, Risk Manager, execution, portfolio, or consensus
    boundaries. ENTER_SHORT_ADVISORY is information only.
    """

    schema_version: int
    idea_id: str
    trader_id: str
    trader_display_name: str
    source_id: str
    source_name: str
    source_type: TraderSourceType
    source_reference: str | None
    published_at: datetime
    ingested_at: datetime
    context: TraderMarketContext
    thesis: TraderThesis
    trade_plan: TraderTradePlan
    suggested_action: TraderSuggestedAction
    edited_after_publication: bool
    ingestion_label: str
    attribution: str
    checksum: str
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    evaluation_status: TraderEvaluationStatus

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported trader idea schema version.")
        for name, value in (
            ("idea_id", self.idea_id),
            ("trader_id", self.trader_id),
            ("trader_display_name", self.trader_display_name),
            ("source_id", self.source_id),
            ("source_name", self.source_name),
            ("ingestion_label", self.ingestion_label),
            ("attribution", self.attribution),
        ):
            _required(value, name)
        if not isinstance(self.source_type, TraderSourceType):
            raise ValueError("source_type must be a TraderSourceType.")
        if not isinstance(self.thesis, TraderThesis):
            raise ValueError("thesis must be a TraderThesis.")
        if not isinstance(self.context, TraderMarketContext):
            raise ValueError("context must be a TraderMarketContext.")
        if not isinstance(self.trade_plan, TraderTradePlan):
            raise ValueError("trade_plan must be a TraderTradePlan.")
        if not isinstance(self.suggested_action, TraderSuggestedAction):
            raise ValueError("suggested_action must be a TraderSuggestedAction.")
        if not isinstance(self.evaluation_status, TraderEvaluationStatus):
            raise ValueError("evaluation_status must be a TraderEvaluationStatus.")
        published = _utc(self.published_at, "published_at")
        ingested = _utc(self.ingested_at, "ingested_at")
        if published > ingested and (published - ingested).total_seconds() > 60:
            raise ValueError("Publication timestamp cannot be unreasonably future-dated.")
        _required(self.checksum, "checksum")

    @classmethod
    def create(
        cls,
        *,
        idea_id: str,
        trader: TraderProfile,
        source: TraderSource,
        published_at: datetime,
        ingested_at: datetime,
        context: TraderMarketContext,
        thesis: TraderThesis,
        trade_plan: TraderTradePlan | None = None,
        suggested_action: TraderSuggestedAction,
        edited_after_publication: bool = False,
        ingestion_label: str = "MANUAL",
        warnings: tuple[str, ...] = (),
        limitations: tuple[str, ...] = (),
        evaluation_status: TraderEvaluationStatus = TraderEvaluationStatus.PENDING,
    ) -> "TraderIdeaRecord":
        """Create a validated trader idea record with a deterministic checksum."""
        published = _utc(published_at, "published_at")
        ingested = _utc(ingested_at, "ingested_at")
        plan = trade_plan or TraderTradePlan()
        payload = (
            idea_id,
            trader.trader_id,
            source.source_id,
            context.symbol,
            context.timeframe,
            published.isoformat(),
            thesis.direction.value,
            thesis.stated_confidence,
            suggested_action.value,
            source.provenance,
        )
        checksum = stable_checksum(payload)
        return cls(
            1,
            idea_id,
            trader.trader_id,
            trader.display_name,
            source.source_id,
            source.source_name,
            source.source_type,
            source.source_reference,
            published,
            ingested,
            context,
            thesis,
            plan,
            suggested_action,
            edited_after_publication,
            ingestion_label,
            trader.attribution,
            checksum,
            warnings,
            limitations or source.limitations,
            evaluation_status,
        )


@dataclass(frozen=True)
class TraderIdeaOutcome:
    """What happened after a trader idea was published.

    Outcomes are advisory and descriptive. They cannot mutate configuration,
    weights, risk limits, or execution state.
    """

    idea_id: str
    evaluated_at: datetime
    horizon_seconds: int
    favorable_movement: float
    adverse_movement: float
    classification: str
    explanation: str
    advisory_only: bool = True

    def __post_init__(self) -> None:
        _required(self.idea_id, "idea_id")
        _utc(self.evaluated_at, "evaluated_at")
        if self.horizon_seconds <= 0:
            raise ValueError("Outcome horizon must be positive.")
        _finite(self.favorable_movement, "favorable_movement")
        _finite(self.adverse_movement, "adverse_movement")
        _required(self.classification, "classification")
        _required(self.explanation, "explanation")
        if not self.advisory_only:
            raise ValueError("Trader idea outcomes must remain advisory.")


@dataclass(frozen=True)
class TraderIdeaImportSummary:
    """Summary of an import operation showing accepted and rejected records."""

    accepted: tuple[TraderIdeaRecord, ...]
    rejected: tuple[tuple[int, str], ...]
    source_type: TraderSourceType

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, TraderSourceType):
            raise ValueError("source_type must be a TraderSourceType.")
        ids = tuple(item.idea_id for item in self.accepted)
        if len(ids) != len(set(ids)):
            raise ValueError("Import summary cannot contain duplicate accepted IDs.")
