"""Immutable multi-symbol scheduler state."""
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class SymbolSchedule:
    symbol: str; enabled: bool = True

@dataclass(frozen=True)
class SymbolRuntimeState:
    symbol: str; enabled: bool; provider_health: str
    last_success: datetime | None; last_failure: datetime | None
    regime: str; multi_timeframe: str
    successful_cycles: int; failed_cycles: int; skipped_cycles: int
    history: tuple[tuple[datetime, str], ...]

@dataclass(frozen=True)
class MultiSymbolRun:
    cycles: int; states: tuple[SymbolRuntimeState, ...]
    ordering: tuple[str, ...]; recovered: bool; stopped_reason: str
    paper_only: bool = True
