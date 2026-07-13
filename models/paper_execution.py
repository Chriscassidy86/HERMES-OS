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
    trade_duration_seconds: float | None = None
    paper_only: bool = True

@dataclass(frozen=True)
class SimulationRules:
    spread_bps:float=2; slippage_bps:float=5; latency_ms:int=50
    partial_fill_ratio:float=1; impact_bps_per_unit:float=0
    timeout_ms:int=1000; minimum_quantity:float=.00000001; minimum_notional:float=1
    quantity_precision:int=8; price_precision:int=2; fee_bps:float=10

@dataclass(frozen=True)
class SimulatedOrder:
    order_id:str; cycle_id:str; symbol:str; side:str; order_type:str
    quantity:float; status:str; created_at:datetime; risk_approved:bool
    limit_price:float|None=None; stop_price:float|None=None; trailing_percent:float|None=None

@dataclass(frozen=True)
class SimulatedFill:
    fill_id:str; order_id:str; cycle_id:str; source:str; timestamp:datetime
    quantity:float; price:float; fee:float; slippage:float
    simulated_latency_ms:int; explanation:str; risk_approved:bool=True
