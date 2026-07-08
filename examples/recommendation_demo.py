from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.evidence_summary import EvidenceSummary
from core.recommendation.recommendation_engine import RecommendationEngine


summary = EvidenceSummary(
    symbol="BTC/USD",
    bullish=2,
    bearish=0,
    neutral=1,
    average_confidence=71.67,
    signal_count=3,
)

engine = RecommendationEngine()

recommendation = engine.recommend(summary)

print("====================================================")
print("      HERMES RECOMMENDATION DEPARTMENT")
print("====================================================")
print()
print(f"Market: {summary.symbol}")
print(f"Recommendation: {recommendation}")
print()
print("Reason:")
print(f"- Bullish Departments: {summary.bullish}")
print(f"- Bearish Departments: {summary.bearish}")
print(f"- Average Confidence: {summary.average_confidence}%")
print("====================================================")