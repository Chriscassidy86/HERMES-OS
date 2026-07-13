"""Immutable later-horizon evaluation of a historical PAPER decision."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DecisionQualityRecord:
 schema_version:int; cycle_id:str; symbol:str; timestamp:str; provider:str; price:float; regime:str; recommendation:str; confidence:float
 risk_result:str; risk_explanation:str; specialist_evidence:tuple; position_open:bool; execution_occurred:bool; evaluation_horizon_seconds:int
 later_price_checkpoints:tuple; outcome_classification:str; maximum_favorable_movement:float; maximum_adverse_movement:float
 wait_hold_avoided_bad_trade:bool; rejected_trade_result:str|None; source_label:str; limitation:str; evaluated_at:str
