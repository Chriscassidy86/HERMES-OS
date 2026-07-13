"""Deterministic relative-volume specialist."""
from agents.base.base_specialist import BaseSpecialist
from models.signal import Signal

class VolumeSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Volume Specialist")
    def analyze(self, snapshot):
        average = snapshot.average_volume
        if average is None or average <= 0:
            direction, status, confidence, strength, fact = "WAIT", "INSUFFICIENT_DATA", 50.0, 0.0, "Average volume is unavailable."
        else:
            ratio = snapshot.volume_24h / average
            rising = snapshot.price >= (snapshot.previous_price or snapshot.price)
            direction = "LONG" if ratio >= 1.2 and rising else ("SHORT" if ratio >= 1.2 else "WAIT")
            status = "CONFIRMING" if direction != "WAIT" else "NEUTRAL"
            confidence = min(65.0 + max(ratio - 1.0, 0) * 25, 88.0) if direction != "WAIT" else 55.0
            strength = min(max(ratio - 1.0, 0), 1.0) if direction != "WAIT" else 0.2
            fact = f"Current volume is {ratio:.2f}x average volume."
        report = self.create_report(status, confidence, [fact], [], "VOLUME_EVIDENCE_ONLY")
        return report, Signal(self.name, direction, confidence, strength, snapshot.timeframe, 3, snapshot.timestamp, (fact,))
