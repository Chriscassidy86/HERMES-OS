"""Deterministic moving-average market regime specialist."""
from agents.base.base_specialist import BaseSpecialist
from models.signal import Signal

class MarketRegimeSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Market Regime Specialist")
    def analyze(self, snapshot):
        short, long = snapshot.short_moving_average, snapshot.long_moving_average
        if short is None or long is None or short <= 0 or long <= 0:
            direction, status, confidence, strength, fact = "WAIT", "INSUFFICIENT_DATA", 50.0, 0.0, "Moving-average inputs are unavailable."
        elif short > long:
            direction, status, confidence, strength, fact = "LONG", "BULLISH", 82.0, 0.82, f"Short MA {short:.2f} is above long MA {long:.2f}."
        elif short < long:
            direction, status, confidence, strength, fact = "SHORT", "BEARISH", 82.0, 0.82, f"Short MA {short:.2f} is below long MA {long:.2f}."
        else:
            direction, status, confidence, strength, fact = "WAIT", "NEUTRAL", 55.0, 0.2, "Moving averages are equal."
        report = self.create_report(status, confidence, [fact], [], "REGIME_EVIDENCE_ONLY")
        return report, Signal(self.name, direction, confidence, strength, snapshot.timeframe, 1, snapshot.timestamp, (fact,))
