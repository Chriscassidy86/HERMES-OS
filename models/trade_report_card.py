"""Immutable PAPER trade validation artifact."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeReportCard:
    schema_version: int
    trade_id: str
    symbol: str
    entry_timestamp: str
    exit_timestamp: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    fees: float
    slippage: float
    return_percentage: float
    duration_seconds: int
    entry_regime: str
    exit_regime: str
    entry_recommendation: str
    entry_confidence: float
    risk_approved: bool
    position_sizing_rationale: str
    entry_specialists: tuple
    exit_specialists: tuple
    supporting_evidence: tuple[str, ...]
    ignored_evidence: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    exit_reason: str
    thesis_matched: bool
    correct_specialists: tuple[str, ...]
    incorrect_specialists: tuple[str, ...]
    calibration_error: float
    learning_recommendations: tuple[str, ...]
    mode: str
    provider_sources: tuple[str, ...]
    limitation: str
