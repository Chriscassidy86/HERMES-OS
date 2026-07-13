"""Immutable performance and human-review learning records."""
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class SpecialistPrediction:
    source:str; direction:str; confidence:float
@dataclass(frozen=True)
class TradeOutcome:
    trade_id:str; symbol:str; direction:str; entry_price:float; exit_price:float
    quantity:float; fees:float; opened_at:datetime; closed_at:datetime
    specialist_predictions:tuple[SpecialistPrediction,...]=()
    @property
    def pnl(self):
        multiplier=1 if self.direction=="LONG" else -1
        return (self.exit_price-self.entry_price)*self.quantity*multiplier-self.fees
    @property
    def winning_direction(self): return "LONG" if self.exit_price>self.entry_price else ("SHORT" if self.exit_price<self.entry_price else "WAIT")
@dataclass(frozen=True)
class SpecialistScorecard:
    source:str; sample_size:int; correct:int; accuracy:float; brier_score:float
@dataclass(frozen=True)
class StrategyScorecard:
    sample_size:int; wins:int; losses:int; win_rate:float; loss_rate:float
    expectancy:float; profit_factor:float|None; average_gain:float
    average_loss:float; maximum_drawdown:float; total_pnl:float
    risk_adjusted_return:float|None
@dataclass(frozen=True)
class DrawdownReport:
    maximum_drawdown:float; ending_equity:float
@dataclass(frozen=True)
class WinLossReport:
    wins:int; losses:int; average_gain:float; average_loss:float; expectancy:float
@dataclass(frozen=True)
class DailyPerformanceReport:
    date:str; strategy:StrategyScorecard; specialists:tuple[SpecialistScorecard,...]
@dataclass(frozen=True)
class WeeklyPerformanceReport:
    week:str; strategy:StrategyScorecard; specialists:tuple[SpecialistScorecard,...]
@dataclass(frozen=True)
class ProposedConfigurationPatch:
    affected_rule:str; current_value:float; proposed_value:float; evidence:str
    sample_size:int; before_estimate:float; after_estimate:float; confidence:float
    risks:tuple[str,...]; human_approval_required:bool=True
