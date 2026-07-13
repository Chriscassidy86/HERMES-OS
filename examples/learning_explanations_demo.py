"""Explain deterministic closed paper outcomes without changing configuration."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from agents.learning import LearningExplanationEngine
from models.performance import SpecialistPrediction, TradeOutcome


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
outcomes = (
    TradeOutcome("PT-1", "BTC/USD", "LONG", 100, 110, 1, 1, NOW, NOW,
                 (SpecialistPrediction("Trend Specialist", "LONG", 80),)),
    TradeOutcome("PT-2", "BTC/USD", "LONG", 110, 100, 1, 1, NOW, NOW,
                 (SpecialistPrediction("Trend Specialist", "LONG", 85),)),
)
report = LearningExplanationEngine().explain(outcomes)
print("PAPER MODE ONLY - POST-TRADE LEARNING")
for trade in report.trades: print(trade.trade_id, trade.outcome, trade.why[0])
print(report.calibration_explanation)
print("Configuration modified:", report.configuration_modified)

