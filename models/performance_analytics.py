"""Immutable advanced performance analytics records."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PerformanceObservation:
    observation_id: str
    observed_at: datetime
    source: str
    symbol: str
    regime: str
    timeframe: str
    specialist: str
    realized_pnl: float
    unrealized_pnl: float
    equity: float
    exposure: float
    turnover: float
    fees: float
    slippage: float
    confidence: float
    correct: bool
    outcome: str
    holding_seconds: float = 0


@dataclass(frozen=True)
class PerformanceGroup:
    label: str
    samples: int
    realized_pnl: float
    win_rate: float | None


@dataclass(frozen=True)
class AdvancedPerformanceReport:
    sample_size: int
    realized_pnl: float
    unrealized_pnl: float
    total_return: float | None
    annualized_return: float | None
    win_rate: float | None
    loss_rate: float | None
    average_win: float | None
    average_loss: float | None
    expectancy: float | None
    profit_factor: float | None
    maximum_drawdown: float | None
    recovery_factor: float | None
    sharpe_style: float | None
    sortino_style: float | None
    average_exposure: float | None
    turnover: float
    fee_impact: float
    slippage_impact: float
    calibration_error: float | None
    rejection_quality: float | None
    no_trade_quality: float | None
    by_symbol: tuple[PerformanceGroup, ...]
    by_regime: tuple[PerformanceGroup, ...]
    by_timeframe: tuple[PerformanceGroup, ...]
    by_specialist: tuple[PerformanceGroup, ...]
    by_source: tuple[PerformanceGroup, ...]
    assumptions: tuple[str, ...]
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class PortfolioAnalyticsProjection:
    report: AdvancedPerformanceReport
    equity_curve: tuple[tuple[datetime,float],...]
    cash_curve: tuple[tuple[datetime,float],...]
    exposure_curve: tuple[tuple[datetime,float],...]
    concentration_risk: float|None
    average_holding_seconds: float|None
    correlations: tuple[tuple[str,str,float],...]
    correlation_state: str
    source_labels: tuple[str,...]
