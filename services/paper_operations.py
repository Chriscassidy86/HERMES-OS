"""Controlled long-running paper operation, recovery, and circuit breaking."""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

from services.paper_session import ScheduledPaperSession


FAILURE_STATUSES = {
    "PROVIDER_FAILURE",
    "DECISION_FAILURE",
    "PERSISTENCE_FAILURE",
    "PAPER_EXECUTION_FAILURE",
}


@dataclass(frozen=True)
class PaperOperationConfig:
    symbols: tuple[str, ...]
    timeframe: str = "4H"
    interval_seconds: float = 30.0
    max_consecutive_failures: int = 3


@dataclass(frozen=True)
class PaperOperationSummary:
    started_at: datetime
    ended_at: datetime
    recovered_portfolio: bool
    batches_completed: int
    status_counts: tuple[tuple[str, int], ...]
    consecutive_failures: int
    stopped_reason: str
    paper_mode_only: bool = True


class PaperOperationsService:
    def __init__(self, session, journal, shutdown, *, clock=None, wait=None):
        self.session = session
        self.journal = journal
        self.shutdown = shutdown
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.wait = wait or shutdown.wait

    def recover(self) -> bool:
        self.journal.validate_schema()
        return self.journal.restore_portfolio(self.session.portfolio)

    def run(
        self, config: PaperOperationConfig, *, maximum_batches: int | None = None
    ) -> PaperOperationSummary:
        self._validate(config, maximum_batches)
        started = self._now()
        recovered = self.recover()
        scheduled = ScheduledPaperSession(self.session)
        counts: dict[str, int] = {}
        batches = consecutive = 0
        stopped_reason = "SHUTDOWN_REQUESTED"
        while not self.shutdown.requested:
            results = scheduled.run_once(config.symbols, config.timeframe)
            batches += 1
            for result in results:
                counts[result.status] = counts.get(result.status, 0) + 1
            if results and all(result.status in FAILURE_STATUSES for result in results):
                consecutive += 1
            else:
                consecutive = 0
            if consecutive >= config.max_consecutive_failures:
                stopped_reason = "FAILURE_CIRCUIT_OPEN"
                break
            if maximum_batches is not None and batches >= maximum_batches:
                stopped_reason = "BATCH_LIMIT_REACHED"
                break
            if self.wait(config.interval_seconds):
                stopped_reason = "SHUTDOWN_REQUESTED"
                break
        return PaperOperationSummary(
            started,
            self._now(),
            recovered,
            batches,
            tuple(sorted(counts.items())),
            consecutive,
            stopped_reason,
        )

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Paper operations clock must be timezone-aware.")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate(config: PaperOperationConfig, maximum_batches: int | None) -> None:
        if not isinstance(config, PaperOperationConfig) or not config.symbols:
            raise ValueError("Paper operation configuration and symbols are required.")
        if any(not isinstance(symbol, str) or not symbol.strip() for symbol in config.symbols):
            raise ValueError("Paper operation symbols must be non-empty strings.")
        if len(set(config.symbols)) != len(config.symbols):
            raise ValueError("Paper operation symbols must be unique.")
        if not config.timeframe.strip():
            raise ValueError("Paper operation timeframe is required.")
        if isinstance(config.interval_seconds, bool) or not isfinite(config.interval_seconds) or config.interval_seconds < 0:
            raise ValueError("Paper operation interval must be finite and non-negative.")
        if (isinstance(config.max_consecutive_failures, bool)
                or not isinstance(config.max_consecutive_failures, int)
                or config.max_consecutive_failures < 1):
            raise ValueError("Failure circuit threshold must be a positive integer.")
        if maximum_batches is not None and (
            isinstance(maximum_batches, bool) or not isinstance(maximum_batches, int) or maximum_batches < 1
        ):
            raise ValueError("Maximum batches must be a positive integer when supplied.")

