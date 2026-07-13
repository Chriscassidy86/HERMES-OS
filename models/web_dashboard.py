"""Immutable, read-only projection for the local operator dashboard."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WebDashboardProjection:
    banner: str
    mode: str
    version: str
    updated_at: str
    refresh_seconds: int
    system_health: str
    provider_health: str
    database_health: str
    active_provider: str
    latest_cycle_time: str | None
    current_recommendation: str
    confidence: float
    risk_status: str
    risk_reason: str
    market_regime: str
    starting_balance: str
    cash: str
    equity: str
    total_return: str
    realized_pnl: str
    unrealized_pnl: str
    exposure: str
    open_position_count: int
    closed_trade_count: int
    fees_paid: str
    slippage_impact: str
    maximum_drawdown: str
    open_positions: tuple
    closed_trades: tuple
    markets: tuple
    specialists: tuple
    explanation: Any
    providers: tuple
    recent_cycles: tuple
    recent_decisions: tuple
    recent_fills: tuple
    recent_trades: tuple
    recent_alerts: tuple
    learning_recommendations: tuple
    charts: Any
    warnings: tuple
    actions: tuple = ()
