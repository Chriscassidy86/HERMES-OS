"""Read-only report service for trader intelligence.

Displays trader, symbol, timeframe, thesis, suggested action, stated
confidence, publication time, source, market regime, short explanation,
evaluation status, and limitations. No dashboard integration, no execution
integration, no consensus weighting, and no automatic learning.
"""

from dataclasses import dataclass

from database.trader_intelligence_repository import TraderIntelligenceRepository
from models.trader_intelligence import TraderIdeaRecord


@dataclass(frozen=True)
class TraderIdeaReportRow:
    """A single read-only report row for a trader idea."""

    trader_display_name: str
    symbol: str
    timeframe: str
    thesis_direction: str
    suggested_action: str
    stated_confidence: float | None
    published_at: str
    source_name: str
    market_regime: str
    explanation: str
    evaluation_status: str
    limitations: tuple[str, ...]
    advisory_only: bool = True


class TraderIntelligenceReportService:
    """Read-only report service over the trader intelligence repository."""

    def __init__(self, repository: TraderIntelligenceRepository):
        self.repository = repository

    def recent(self, limit: int = 20) -> tuple[TraderIdeaReportRow, ...]:
        ideas = self.repository.recent_ideas(limit)
        return tuple(self._row(item) for item in ideas)

    def by_symbol(self, symbol: str, limit: int = 100) -> tuple[TraderIdeaReportRow, ...]:
        ideas = self.repository.ideas_by_symbol(symbol, limit)
        return tuple(self._row(item) for item in ideas)

    def by_trader(self, trader_id: str, limit: int = 100) -> tuple[TraderIdeaReportRow, ...]:
        ideas = self.repository.ideas_by_trader(trader_id, limit)
        return tuple(self._row(item) for item in ideas)

    def by_regime(self, market_regime: str, limit: int = 100) -> tuple[TraderIdeaReportRow, ...]:
        ideas = self.repository.ideas_by_regime(market_regime, limit)
        return tuple(self._row(item) for item in ideas)

    def unresolved(self, limit: int = 100) -> tuple[TraderIdeaReportRow, ...]:
        ideas = self.repository.unresolved_ideas(limit)
        return tuple(self._row(item) for item in ideas)

    @staticmethod
    def _row(record: TraderIdeaRecord) -> TraderIdeaReportRow:
        return TraderIdeaReportRow(
            record.trader_display_name,
            record.context.symbol,
            record.context.timeframe,
            record.thesis.direction.value,
            record.suggested_action.value,
            record.thesis.stated_confidence,
            record.published_at.isoformat(),
            record.source_name,
            record.context.market_regime,
            record.thesis.explanation,
            record.evaluation_status.value,
            record.limitations,
        )

    @staticmethod
    def to_json(rows: tuple[TraderIdeaReportRow, ...]) -> str:
        import json

        from dataclasses import asdict

        return json.dumps([asdict(row) for row in rows], sort_keys=True, separators=(",", ":"), default=str)
