"""Immutable local web dashboard projection."""
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class WebDashboardProjection:
    banner:str; mode:str; version:str; system_health:str; provider_health:str; database_health:str
    latest_decision:Any; market_regime:str; multi_timeframe_alignment:Any; specialists:tuple
    agreements:tuple; disagreements:tuple; ignored_evidence:tuple; risk_decision:Any
    cash:str; equity:str; exposure:str; open_positions:tuple; closed_trades:tuple
    daily_pnl:str; weekly_pnl:str; total_return:str; maximum_drawdown:str
    win_rate:str; profit_factor:str|None; warnings:tuple; executive_brief:Any
    learning_explanation:Any; experiment_status:Any; research_run:Any; actions:tuple=()
    latest_trade:Any=None; recent_alerts:tuple=(); operator_workflow:Any=None; refresh_seconds:int=5
