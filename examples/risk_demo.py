from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.recommendation import Recommendation
from core.risk.risk_manager import RiskManager


recommendation = Recommendation(
    symbol="BTC/USD",
    action="LONG",
    confidence=71.67,
    reason="Bullish evidence exceeds bearish evidence.",
)

risk = RiskManager()

assessment = risk.evaluate(recommendation)

print("====================================================")
print("           HERMES RISK DEPARTMENT")
print("====================================================")
print()

print(f"Market: {assessment.symbol}")
print(f"Approved: {assessment.approved}")
print(f"Risk Score: {assessment.risk_score}")
print(f"Maximum Position: ${assessment.max_position_size:.2f}")
print(f"Maximum Loss: ${assessment.max_loss:.2f}")
print(f"Reason: {assessment.reason}")

print()
print("====================================================")
