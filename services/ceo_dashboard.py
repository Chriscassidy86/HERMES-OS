"""Compose CEO research state while keeping presentation and actions separate."""

from models.ceo_dashboard import CEODashboardView, ExperimentDashboardStatus


class CEODashboardService:
    def __init__(self, command_center_service):
        self.command_center_service = command_center_service

    def build(self, *, regime=None, multi_timeframe=None,
              learning_recommendations=(), experiments=()):
        command = self.command_center_service.build(
            learning_recommendations=learning_recommendations
        )
        latest = command.latest_cycle or {}
        recommendation = latest.get("recommendation") or {}
        risk = latest.get("risk_assessment") or {}
        market_regime = (
            regime.regime.value if regime is not None else command.market_regime
        )
        confidence = (
            multi_timeframe.confidence if multi_timeframe is not None
            else float(recommendation.get("confidence", 0))
        )
        specialist_views = (
            multi_timeframe.specialists if multi_timeframe is not None
            else command.specialists
        )
        statuses = tuple(sorted((self._experiment_status(item) for item in experiments),
                                key=lambda item: item.experiment_id))
        return CEODashboardView(
            command.banner, command.cash, command.equity, command.open_positions,
            command.closed_trades, specialist_views, market_regime, confidence,
            recommendation.get("action", "WAIT"),
            "APPROVED" if risk.get("approved", False) else "REJECTED",
            risk.get("reason", "No Risk Manager decision is available."),
            command.executive_summary, command.system_health, command.provider_health,
            command.database_health, command.learning_recommendations, statuses,
            command.decision_explanation,
        )

    @staticmethod
    def _experiment_status(result):
        definition = result.definition
        return ExperimentDashboardStatus(
            definition.experiment_id,
            result.status.value,
            result.sample_size,
            result.human_review_required,
            result.production_change_applied,
        )

