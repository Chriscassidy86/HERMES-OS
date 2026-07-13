"""Immutable explainable PAPER execution outcome."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class PaperExecutionOutcome:
    action: str
    status: str
    symbol: str
    timestamp: datetime
    confidence: float
    risk_approved: bool
    risk_reason: str
    market_regime: str
    specialist_summary: tuple[str, ...]
    decision_explanation: str
    order: Any = None
    fill: Any = None
    trade: Any = None
    paper_only: bool = True
