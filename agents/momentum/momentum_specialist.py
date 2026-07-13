"""Deterministic price-change momentum specialist."""
from agents.base.base_specialist import BaseSpecialist
from models.signal import Signal

class MomentumSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Momentum Specialist")
    def analyze(self, snapshot):
        previous = snapshot.previous_price
        if previous is None or previous <= 0:
            direction, status, confidence, strength, fact = "WAIT", "INSUFFICIENT_DATA", 50.0, 0.0, "Previous price is unavailable."
        else:
            change = (snapshot.price - previous) / previous * 100
            direction, status = (("LONG", "BULLISH") if change >= 0.5 else (("SHORT", "BEARISH") if change <= -0.5 else ("WAIT", "NEUTRAL")))
            strength = min(abs(change) / 3.0, 1.0) if direction != "WAIT" else 0.2
            confidence = min(70.0 + abs(change) * 5, 90.0) if direction != "WAIT" else 55.0
            fact = f"Price changed {change:.2f}% from the previous observation."
        report = self.create_report(status, confidence, [fact], [], "MOMENTUM_EVIDENCE_ONLY")
        return report, Signal(self.name, direction, confidence, strength, snapshot.timeframe, 2, snapshot.timestamp, (fact,))
