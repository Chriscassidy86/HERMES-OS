"""Deterministic volatility-state specialist."""
from agents.base.base_specialist import BaseSpecialist
from models.signal import Signal

class VolatilitySpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Volatility Specialist")
    def analyze(self, snapshot):
        if snapshot.volatility > 6.0:
            direction, status, confidence, strength, fact = "WAIT", "HIGH_RISK", 85.0, 0.0, f"Volatility {snapshot.volatility:.2f}% exceeds the safe range."
        elif snapshot.volatility <= 3.0:
            direction = "LONG" if snapshot.market_trend.lower() == "bullish" else ("SHORT" if snapshot.market_trend.lower() == "bearish" else "WAIT")
            status, confidence, strength, fact = "STABLE", 75.0, 0.65, f"Volatility {snapshot.volatility:.2f}% supports the stated trend."
        else:
            direction, status, confidence, strength, fact = "WAIT", "ELEVATED", 60.0, 0.2, f"Volatility {snapshot.volatility:.2f}% is elevated."
        report = self.create_report(status, confidence, [fact], [], "VOLATILITY_EVIDENCE_ONLY")
        return report, Signal(self.name, direction, confidence, strength, snapshot.timeframe, 2, snapshot.timestamp, (fact,))
