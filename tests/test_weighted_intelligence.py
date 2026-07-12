"""Foundation IV.2 weighted intelligence tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest
from agents.base.base_specialist import BaseSpecialist
from agents.trend.trend_specialist import TrendSpecialist
from core.decision_cycle import DecisionCycle
from core.evidence.evidence_analyzer import EvidenceAnalyzer
from models.decision_packet import DecisionPacket
from models.signal import Signal
from reports.market_snapshot import MarketSnapshot

NOW = datetime(2026, 7, 11, 12, tzinfo=timezone.utc)
SOURCES = ("Trend Specialist", "Market Regime Specialist", "Momentum Specialist", "Volume Specialist", "Volatility Specialist")
def signal(source, direction="LONG", confidence=80.0, timeframe="4H", timestamp=NOW):
    return Signal(source, direction, confidence, 0.8, timeframe, 2, timestamp, ("test evidence",))
def summary(*signals):
    return EvidenceAnalyzer().analyze(DecisionPacket("BTC/USD", tuple(signals), NOW), as_of=NOW)
def snapshot(trend="Bullish"):
    bullish = trend == "Bullish"
    return MarketSnapshot("BTC/USD", 102.0 if bullish else 98.0, 1500.0, trend, 2.0, 55,
                          100.0, 1000.0, 101.0 if bullish else 99.0,
                          99.0 if bullish else 101.0, "4H", NOW)
class BrokenSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Broken Specialist")
    def analyze(self, snapshot): raise RuntimeError("expected failure")
class StaleSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Trend Specialist")
    def analyze(self,snapshot):
        report=self.create_report("BULLISH",80,["stale"],[],"EVIDENCE_ONLY")
        return report,Signal(self.name,"LONG",80,0.8,"4H",2,NOW-timedelta(hours=5),("stale",))
class FutureSignalSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Trend Specialist")
    def analyze(self,snapshot):
        report=self.create_report("BULLISH",80,["future"],[],"EVIDENCE_ONLY")
        return report,Signal(self.name,"LONG",80,0.8,"4H",2,NOW+timedelta(minutes=5),("future",))
class WeightedEvidenceTests(unittest.TestCase):
    def test_trend_explanation_matches_direction(self):
        _,bullish=TrendSpecialist().analyze(snapshot("Bullish"))
        _,bearish=TrendSpecialist().analyze(snapshot("Bearish"))
        self.assertIn("bullish",bullish.evidence[0]); self.assertIn("bearish",bearish.evidence[0])
    def test_unanimous_bullish(self):
        result = summary(*(signal(source) for source in SOURCES))
        self.assertEqual(5, result.bullish); self.assertGreater(result.directional_score, 0.79)
    def test_unanimous_bearish(self):
        result = summary(*(signal(source, "SHORT") for source in SOURCES))
        self.assertEqual(5, result.bearish); self.assertLess(result.directional_score, -0.79)
    def test_mixed_evidence(self):
        result = summary(signal(SOURCES[0]), signal(SOURCES[1], "SHORT"))
        self.assertTrue(result.conflicting_evidence); self.assertLess(result.final_confidence, 10)
    def test_neutral_only(self):
        self.assertEqual(0.0, summary(*(signal(s, "WAIT", 95.0) for s in SOURCES)).final_confidence)
    def test_stale_evidence(self):
        result = summary(signal(SOURCES[0], timestamp=NOW - timedelta(hours=5)))
        self.assertEqual(0.0, result.final_confidence); self.assertIn("stale", result.excluded_evidence[0])
    def test_low_confidence(self):
        result = summary(signal(SOURCES[0], confidence=49.0))
        self.assertTrue(result.excluded_evidence); self.assertEqual(0, result.bullish)
    def test_conflicting_timeframe(self):
        self.assertIn("incompatible", summary(signal(SOURCES[0], timeframe="1D")).excluded_evidence[0])
    def test_specialist_failure(self):
        result = DecisionCycle([BrokenSpecialist()], clock=lambda: NOW).run(snapshot())
        self.assertFalse(result.paper_execution_eligible); self.assertEqual("REJECTED_INVALID_EVIDENCE", result.final_status)
    def test_malformed_evidence(self):
        malformed = replace(signal(SOURCES[0]), evidence=())
        class Specialist(BaseSpecialist):
            def __init__(self): super().__init__(SOURCES[0])
            def analyze(self, snapshot): return self.create_report("BULLISH", 80, ["x"], [], "x"), malformed
        self.assertFalse(DecisionCycle([Specialist()], clock=lambda: NOW).run(snapshot()).paper_execution_eligible)
    def test_deterministic_five_specialist_cycle(self):
        first = DecisionCycle(clock=lambda: NOW).run(snapshot())
        second = DecisionCycle(clock=lambda: NOW).run(snapshot())
        self.assertEqual(first, second); self.assertEqual(5, len(first.specialist_reports))
    def test_contradictory_cycle_fails_closed(self):
        conflicted=replace(snapshot(),short_moving_average=99.0,long_moving_average=101.0)
        result=DecisionCycle(clock=lambda:NOW).run(conflicted)
        self.assertEqual("REJECTED_INVALID_EVIDENCE",result.final_status); self.assertFalse(result.paper_execution_eligible); self.assertTrue(any("Contradictory" in reason for reason in result.rejection_reasons))
    def test_stale_signal_makes_cycle_invalid(self):
        result=DecisionCycle([StaleSpecialist()],clock=lambda:NOW).run(snapshot())
        self.assertEqual("REJECTED_INVALID_EVIDENCE",result.final_status); self.assertTrue(any("Excluded evidence" in reason for reason in result.rejection_reasons))
    def test_future_snapshot_fails_closed(self):
        future=replace(snapshot(),timestamp=NOW+timedelta(minutes=5))
        result=DecisionCycle(clock=lambda:NOW).run(future)
        self.assertEqual("REJECTED_INVALID_EVIDENCE",result.final_status); self.assertFalse(result.paper_execution_eligible)
    def test_future_signal_fails_closed(self):
        result=DecisionCycle([FutureSignalSpecialist()],clock=lambda:NOW).run(snapshot())
        self.assertEqual("REJECTED_INVALID_EVIDENCE",result.final_status); self.assertTrue(any("future" in reason.lower() for reason in result.rejection_reasons))
if __name__ == "__main__": unittest.main()
