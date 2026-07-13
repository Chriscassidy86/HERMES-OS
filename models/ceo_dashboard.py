"""Immutable CEO dashboard projection with no action controls."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ExperimentDashboardStatus:
    experiment_id: str
    status: str
    sample_size: int
    human_review_required: bool
    production_change_applied: bool


@dataclass(frozen=True)
class CEODashboardView:
    banner: str
    cash: Decimal
    equity: Decimal
    open_positions: tuple
    closed_trades: tuple
    specialists: tuple
    market_regime: str
    confidence: float
    current_recommendation: str
    risk_manager_decision: str
    risk_manager_reason: str
    executive_summary: str
    system_health: str
    provider_health: str
    database_health: str
    learning_recommendations: tuple
    experiment_status: tuple[ExperimentDashboardStatus, ...]
    decision_explanation: Any
    actions: tuple = ()

