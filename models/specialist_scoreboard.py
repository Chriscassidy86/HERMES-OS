"""Immutable read-only specialist validation scoreboard."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SpecialistScore:
    specialist:str; total_eligible_calls:int; correct_calls:int; incorrect_calls:int; neutral_calls:int; excluded_calls:int
    accuracy:float|None; weighted_accuracy:float|None; average_confidence:float|None; calibration_score:float|None
    by_symbol:tuple; by_regime:tuple; by_timeframe:tuple; winning_trade_accuracy:float|None; losing_trade_accuracy:float|None
    recent_streak:int; sample_size_warning:str|None; last_evaluated_timestamp:str|None

@dataclass(frozen=True)
class SpecialistScoreboard:
    generated_at:str; scores:tuple[SpecialistScore,...]; recommendations_only:bool=True; configuration_mutated:bool=False
