from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from agents.learning.learning_engine import LearningEngine
from agents.performance.performance_engine import PerformanceEngine
from models.performance import SpecialistPrediction,TradeOutcome
now=datetime.now(timezone.utc); outcomes=tuple(TradeOutcome(str(i),"BTC/USD","LONG",100,110,1,1,now,now,(SpecialistPrediction("Trend Specialist","LONG",80),)) for i in range(5))
engine=PerformanceEngine(); score=engine.strategy_scorecard(outcomes); specialist=engine.specialist_scorecards(outcomes)[0]; proposal=LearningEngine().recommend_weight_change(specialist,1.0)
print("PAPER MODE ONLY"); print("Trades:",score.sample_size,"P&L:",score.total_pnl,"Win rate:",score.win_rate); print("Proposed rule:",proposal.affected_rule,proposal.current_value,"->",proposal.proposed_value); print("Human approval required:",proposal.human_approval_required); print("Configuration modified: False")
