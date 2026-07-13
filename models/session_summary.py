"""Immutable hourly, daily, or weekly PAPER session summary."""
from dataclasses import dataclass
@dataclass(frozen=True)
class PaperSessionSummary:
 schema_version:int; summary_id:str; period:str; started_at:str; ended_at:str; starting_equity:float; ending_equity:float; realized_pnl:float; unrealized_pnl:float
 fees:float; slippage:float; cycles:int; buy_decisions:int; sell_decisions:int; hold_decisions:int; wait_decisions:int; risk_approvals:int; risk_rejections:int
 paper_fills:int; completed_trades:int; winners:int; losers:int; break_even:int; win_rate:float|None; expectancy:float|None; profit_factor:float|None
 maximum_drawdown:float; best_symbol:str|None; worst_symbol:str|None; best_regime:str|None; worst_regime:str|None; strongest_specialist:str|None; weakest_specialist:str|None
 provider_failures:int; stale_data_rejections:int; alerts:tuple; learning_recommendations:tuple; limitations:tuple[str,...]; mode:str="PAPER ONLY"
