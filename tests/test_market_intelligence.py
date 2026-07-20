"""
Unit tests for the Market Intelligence framework.

Verifies:
  - advisory_only always True
  - report serialization and determinism
  - metadata completeness
  - invalid confidence rejected
  - future timestamps rejected
  - stale timestamps handled safely
  - base specialist interface contract
  - enum completeness
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest

from agents.market_intelligence.base import MarketIntelligenceSpecialist
from models.market_intelligence import (
    AgentStatus,
    HealthCheckResult,
    MarketIntelligenceContext,
    MarketIntelligenceReport,
    MarketRegime,
    SpecialistMetadata,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
FRESH = NOW - timedelta(minutes=5)
STALE = NOW - timedelta(hours=48)


class StubSpecialist(MarketIntelligenceSpecialist):
    """Minimal concrete specialist for testing the base interface."""

    VERSION = "1.0.0"
    SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD")
    SUPPORTED_TIMEFRAMES = ("1H", "4H", "1D")

    def __init__(self):
        super().__init__("Stub Intelligence Specialist")
        self._set_status(AgentStatus.ONLINE)

    def analyze(self, context: MarketIntelligenceContext) -> MarketIntelligenceReport:
        return MarketIntelligenceReport.create(
            agent_name=self.name,
            symbol=context.symbol,
            timeframe=context.timeframe,
            observed_at=context.observed_at,
            confidence=0.75,
            evidence=("Stub evidence line one.", "Stub evidence line two."),
            conflicting_evidence=("Minor conflicting signal.",),
            warnings=("Stub warning.",),
            explanation="Stub specialist produced a deterministic advisory report.",
            now=NOW,
        )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class MarketRegimeEnumTests(unittest.TestCase):
    def test_all_required_regimes_exist(self):
        expected = {
            "STRONG_BULL_TREND",
            "WEAK_BULL_TREND",
            "RANGE_BOUND",
            "WEAK_BEAR_TREND",
            "STRONG_BEAR_TREND",
            "HIGH_VOLATILITY_TRANSITION",
            "INSUFFICIENT_DATA",
        }
        actual = {member.name for member in MarketRegime}
        self.assertEqual(expected, actual)

    def test_regime_values_match_names(self):
        for member in MarketRegime:
            self.assertEqual(member.name, member.value)

    def test_insufficient_data_is_available(self):
        self.assertEqual(
            MarketRegime.INSUFFICIENT_DATA.value, "INSUFFICIENT_DATA"
        )


class AgentStatusEnumTests(unittest.TestCase):
    def test_all_required_statuses_exist(self):
        expected = {"ONLINE", "OFFLINE", "STARTING", "ERROR", "DEGRADED"}
        actual = {member.name for member in AgentStatus}
        self.assertEqual(expected, actual)

    def test_status_values_match_names(self):
        for member in AgentStatus:
            self.assertEqual(member.name, member.value)


# ---------------------------------------------------------------------------
# MarketIntelligenceReport tests
# ---------------------------------------------------------------------------


class MarketIntelligenceReportTests(unittest.TestCase):
    def _make_report(self, **overrides) -> MarketIntelligenceReport:
        defaults = dict(
            agent_name="Test Specialist",
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            confidence=0.80,
            evidence=("Price above moving average.",),
            conflicting_evidence=(),
            warnings=(),
            explanation="Bullish evidence detected.",
            now=NOW,
        )
        defaults.update(overrides)
        return MarketIntelligenceReport.create(**defaults)

    # -- advisory_only enforcement -----------------------------------------

    def test_advisory_only_is_true_by_default(self):
        report = self._make_report()
        self.assertTrue(report.advisory_only)

    def test_advisory_only_false_is_rejected(self):
        with self.assertRaises(ValueError):
            MarketIntelligenceReport(
                agent_name="Test Specialist",
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=FRESH,
                confidence=0.80,
                evidence=("Evidence.",),
                conflicting_evidence=(),
                warnings=(),
                explanation="Explanation.",
                advisory_only=False,
            )

    # -- serialization and determinism -------------------------------------

    def test_serialization_is_deterministic(self):
        report = self._make_report()
        json1 = report.to_json()
        json2 = report.to_json()
        self.assertEqual(json1, json2)

    def test_checksum_is_stable(self):
        report = self._make_report()
        self.assertEqual(report.checksum(), report.checksum())

    def test_identical_reports_have_identical_checksums(self):
        r1 = self._make_report()
        r2 = self._make_report()
        self.assertEqual(r1.checksum(), r2.checksum())

    def test_different_reports_have_different_checksums(self):
        r1 = self._make_report(confidence=0.80)
        r2 = self._make_report(confidence=0.70)
        self.assertNotEqual(r1.checksum(), r2.checksum())

    def test_to_dict_contains_all_fields(self):
        report = self._make_report()
        d = report.to_dict()
        for field in (
            "agent_name",
            "symbol",
            "timeframe",
            "observed_at",
            "confidence",
            "evidence",
            "conflicting_evidence",
            "warnings",
            "explanation",
            "advisory_only",
        ):
            self.assertIn(field, d)
        self.assertTrue(d["advisory_only"])

    def test_serialized_timestamp_is_utc_iso(self):
        report = self._make_report()
        d = report.to_dict()
        self.assertTrue(d["observed_at"].endswith("+00:00"))

    # -- confidence validation ---------------------------------------------

    def test_confidence_below_zero_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(confidence=-0.01)

    def test_confidence_above_one_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(confidence=1.01)

    def test_confidence_zero_accepted(self):
        report = self._make_report(confidence=0.0)
        self.assertEqual(report.confidence, 0.0)

    def test_confidence_one_accepted(self):
        report = self._make_report(confidence=1.0)
        self.assertEqual(report.confidence, 1.0)

    def test_confidence_nan_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(confidence=float("nan"))

    def test_confidence_inf_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(confidence=float("inf"))

    def test_confidence_bool_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(confidence=True)

    # -- timestamp validation -----------------------------------------------

    def test_future_timestamp_rejected(self):
        future = NOW + timedelta(hours=1)
        with self.assertRaises(ValueError):
            self._make_report(observed_at=future, now=NOW)

    def test_naive_timestamp_rejected(self):
        naive = datetime(2026, 7, 13, 12, 0, 0)
        with self.assertRaises(ValueError):
            self._make_report(observed_at=naive, now=NOW)

    def test_stale_timestamp_handled_safely(self):
        report = self._make_report(observed_at=STALE, now=NOW)
        self.assertTrue(report.advisory_only)
        stale_warnings = [w for w in report.warnings if "stale" in w.lower()]
        self.assertEqual(len(stale_warnings), 1)

    def test_fresh_timestamp_has_no_stale_warning(self):
        report = self._make_report(observed_at=FRESH, now=NOW)
        stale_warnings = [w for w in report.warnings if "stale" in w.lower()]
        self.assertEqual(len(stale_warnings), 0)

    def test_custom_stale_threshold(self):
        slightly_stale = NOW - timedelta(seconds=120)
        report = self._make_report(
            observed_at=slightly_stale, now=NOW, stale_threshold_seconds=60
        )
        stale_warnings = [w for w in report.warnings if "stale" in w.lower()]
        self.assertEqual(len(stale_warnings), 1)

    # -- immutability -------------------------------------------------------

    def test_report_is_immutable(self):
        report = self._make_report()
        with self.assertRaises(FrozenInstanceError):
            report.confidence = 0.50

    # -- required field validation -----------------------------------------

    def test_empty_agent_name_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(agent_name="")

    def test_empty_symbol_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(symbol="")

    def test_empty_timeframe_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(timeframe="")

    def test_empty_explanation_rejected(self):
        with self.assertRaises(ValueError):
            self._make_report(explanation="")

    def test_non_tuple_evidence_rejected(self):
        with self.assertRaises(ValueError):
            MarketIntelligenceReport(
                agent_name="Test",
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=FRESH,
                confidence=0.5,
                evidence=["Not a tuple"],
                conflicting_evidence=(),
                warnings=(),
                explanation="Explanation.",
            )


# ---------------------------------------------------------------------------
# SpecialistMetadata tests
# ---------------------------------------------------------------------------


class SpecialistMetadataTests(unittest.TestCase):
    def test_metadata_completeness(self):
        meta = SpecialistMetadata(
            name="Test Specialist",
            version="1.2.3",
            status=AgentStatus.ONLINE,
            supported_symbols=("BTC/USD", "ETH/USD"),
            supported_timeframes=("1H", "4H"),
        )
        self.assertEqual(meta.name, "Test Specialist")
        self.assertEqual(meta.version, "1.2.3")
        self.assertEqual(meta.status, AgentStatus.ONLINE)
        self.assertEqual(meta.supported_symbols, ("BTC/USD", "ETH/USD"))
        self.assertEqual(meta.supported_timeframes, ("1H", "4H"))
        self.assertTrue(meta.advisory_only)

    def test_metadata_advisory_only_false_rejected(self):
        with self.assertRaises(ValueError):
            SpecialistMetadata(
                name="Test",
                version="1.0.0",
                status=AgentStatus.ONLINE,
                supported_symbols=(),
                supported_timeframes=(),
                advisory_only=False,
            )

    def test_metadata_serialization_is_deterministic(self):
        meta = SpecialistMetadata(
            name="Test",
            version="1.0.0",
            status=AgentStatus.ONLINE,
            supported_symbols=("BTC/USD",),
            supported_timeframes=("4H",),
        )
        self.assertEqual(meta.to_json(), meta.to_json())

    def test_metadata_non_enum_status_rejected(self):
        with self.assertRaises(ValueError):
            SpecialistMetadata(
                name="Test",
                version="1.0.0",
                status="ONLINE",
                supported_symbols=(),
                supported_timeframes=(),
            )

    def test_metadata_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            SpecialistMetadata(
                name="",
                version="1.0.0",
                status=AgentStatus.ONLINE,
                supported_symbols=(),
                supported_timeframes=(),
            )

    def test_metadata_empty_version_rejected(self):
        with self.assertRaises(ValueError):
            SpecialistMetadata(
                name="Test",
                version="",
                status=AgentStatus.ONLINE,
                supported_symbols=(),
                supported_timeframes=(),
            )


# ---------------------------------------------------------------------------
# HealthCheckResult tests
# ---------------------------------------------------------------------------


class HealthCheckResultTests(unittest.TestCase):
    def test_health_check_result_is_advisory(self):
        result = HealthCheckResult(
            agent_name="Test",
            status=AgentStatus.ONLINE,
            healthy=True,
            explanation="OK",
            checked_at=NOW,
        )
        self.assertTrue(result.advisory_only)

    def test_health_check_advisory_only_false_rejected(self):
        with self.assertRaises(ValueError):
            HealthCheckResult(
                agent_name="Test",
                status=AgentStatus.ONLINE,
                healthy=True,
                explanation="OK",
                checked_at=NOW,
                advisory_only=False,
            )

    def test_health_check_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            HealthCheckResult(
                agent_name="Test",
                status=AgentStatus.ONLINE,
                healthy=True,
                explanation="OK",
                checked_at=datetime(2026, 7, 13, 12, 0, 0),
            )

    def test_health_check_serialization_is_deterministic(self):
        result = HealthCheckResult(
            agent_name="Test",
            status=AgentStatus.ONLINE,
            healthy=True,
            explanation="OK",
            checked_at=NOW,
        )
        self.assertEqual(result.to_json(), result.to_json())


# ---------------------------------------------------------------------------
# MarketIntelligenceContext tests
# ---------------------------------------------------------------------------


class MarketIntelligenceContextTests(unittest.TestCase):
    def test_context_validates_required_fields(self):
        ctx = MarketIntelligenceContext(
            symbol="BTC/USD", timeframe="4H", observed_at=FRESH
        )
        self.assertEqual(ctx.symbol, "BTC/USD")
        self.assertEqual(ctx.timeframe, "4H")

    def test_context_empty_symbol_rejected(self):
        with self.assertRaises(ValueError):
            MarketIntelligenceContext(symbol="", timeframe="4H", observed_at=FRESH)

    def test_context_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            MarketIntelligenceContext(
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=datetime(2026, 7, 13, 12, 0, 0),
            )

    def test_context_is_immutable(self):
        ctx = MarketIntelligenceContext(
            symbol="BTC/USD", timeframe="4H", observed_at=FRESH
        )
        with self.assertRaises(FrozenInstanceError):
            ctx.symbol = "ETH/USD"


# ---------------------------------------------------------------------------
# Base specialist interface tests
# ---------------------------------------------------------------------------


class MarketIntelligenceSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.specialist = StubSpecialist()

    def test_name_property(self):
        self.assertEqual(self.specialist.name, "Stub Intelligence Specialist")

    def test_version_property(self):
        self.assertEqual(self.specialist.version, "1.0.0")

    def test_status_property(self):
        self.assertEqual(self.specialist.status, AgentStatus.ONLINE)

    def test_supported_symbols_property(self):
        self.assertEqual(self.specialist.supported_symbols, ("BTC/USD", "ETH/USD"))

    def test_supported_timeframes_property(self):
        self.assertEqual(self.specialist.supported_timeframes, ("1H", "4H", "1D"))

    def test_analyze_returns_advisory_report(self):
        ctx = MarketIntelligenceContext(
            symbol="BTC/USD", timeframe="4H", observed_at=FRESH
        )
        report = self.specialist.analyze(ctx)
        self.assertIsInstance(report, MarketIntelligenceReport)
        self.assertTrue(report.advisory_only)
        self.assertEqual(report.agent_name, self.specialist.name)

    def test_metadata_returns_complete_metadata(self):
        meta = self.specialist.metadata()
        self.assertIsInstance(meta, SpecialistMetadata)
        self.assertEqual(meta.name, self.specialist.name)
        self.assertEqual(meta.version, self.specialist.version)
        self.assertEqual(meta.status, self.specialist.status)
        self.assertEqual(meta.supported_symbols, self.specialist.supported_symbols)
        self.assertEqual(meta.supported_timeframes, self.specialist.supported_timeframes)
        self.assertTrue(meta.advisory_only)

    def test_health_check_returns_valid_result(self):
        result = self.specialist.health_check(now=NOW)
        self.assertIsInstance(result, HealthCheckResult)
        self.assertEqual(result.agent_name, self.specialist.name)
        self.assertEqual(result.status, AgentStatus.ONLINE)
        self.assertTrue(result.healthy)
        self.assertTrue(result.advisory_only)

    def test_health_check_degraded_is_not_healthy_but_advisory(self):
        self.specialist._set_status(AgentStatus.DEGRADED)
        result = self.specialist.health_check(now=NOW)
        self.assertTrue(result.healthy)
        self.assertTrue(result.advisory_only)

    def test_health_check_error_is_not_healthy(self):
        self.specialist._set_status(AgentStatus.ERROR)
        result = self.specialist.health_check(now=NOW)
        self.assertFalse(result.healthy)
        self.assertTrue(result.advisory_only)

    def test_health_check_offline_is_not_healthy(self):
        self.specialist._set_status(AgentStatus.OFFLINE)
        result = self.specialist.health_check(now=NOW)
        self.assertFalse(result.healthy)
        self.assertTrue(result.advisory_only)

    def test_health_check_starting_is_not_healthy(self):
        self.specialist._set_status(AgentStatus.STARTING)
        result = self.specialist.health_check(now=NOW)
        self.assertFalse(result.healthy)
        self.assertTrue(result.advisory_only)

    def test_empty_name_rejected(self):
        class BadSpecialist(MarketIntelligenceSpecialist):
            def analyze(self, context):
                pass

        with self.assertRaises(ValueError):
            BadSpecialist("")

    def test_cannot_instantiate_abstract_base(self):
        with self.assertRaises(TypeError):
            MarketIntelligenceSpecialist("Test")


if __name__ == "__main__":
    unittest.main()
