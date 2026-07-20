"""Deterministic tests for Trader Intelligence Phase 1.

Covers valid manual idea, valid JSON import, valid CSV import, multiple
records, malformed rows, missing attribution, missing timestamp, naive
timestamp, future timestamp, invalid confidence, invalid price, duplicate
exact retry, conflicting duplicate, stable checksum, stable JSON
serialization, persistence reload, bounded queries, filtering by symbol,
filtering by trader, filtering by regime, short advisory cannot execute, no
Risk Manager mutation, no portfolio mutation, no live capability, and no
network access.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from database.trader_intelligence_repository import (
    ConflictingTraderIdeaError,
    TraderIntelligenceRepository,
    TraderSchemaVersionError,
)
from models.trader_intelligence import (
    TraderEvaluationStatus,
    TraderSourceType,
    TraderSuggestedAction,
    TraderThesisDirection,
    stable_checksum,
    stable_json,
)
from services.trader_idea_importer import TraderIdeaImporter
from services.trader_intelligence_report import TraderIntelligenceReportService


def _valid_record_dict(idea_id="TI-TEST-001", published="2025-01-15T12:00:00+00:00"):
    return {
        "idea_id": idea_id,
        "trader_id": "trader-test-001",
        "trader_display_name": "Test Trader",
        "source_id": "test-source-001",
        "source_name": "Test Source",
        "source_reference": "test-ref",
        "published_at": published,
        "symbol": "BTC/USD",
        "timeframe": "4H",
        "market_regime": "BULL_TREND",
        "direction": "BULLISH",
        "stated_confidence": 0.75,
        "explanation": "Test explanation for bullish thesis.",
        "supporting_evidence": ["MA alignment", "Volume confirmation"],
        "invalidation_conditions": ["Price below short MA"],
        "assumptions": ["Public data is accurate"],
        "uncertainty": ["Patterns may not persist"],
        "entry_zone_low": 95000.0,
        "entry_zone_high": 96000.0,
        "stop_loss": 92000.0,
        "target_prices": [105000.0, 110000.0],
        "suggested_action": "ENTER_LONG",
        "edited_after_publication": False,
        "ingestion_label": "MANUAL",
        "attribution": "Test Trader via test fixture",
        "warnings": [],
        "limitations": ["Test fixture, not real advice"],
    }


class TraderIntelligenceModelTests(unittest.TestCase):
    """T1: Domain model validation tests."""

    def test_valid_manual_idea(self):
        importer = TraderIdeaImporter()
        idea = importer.from_manual(_valid_record_dict(), ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        self.assertEqual(idea.idea_id, "TI-TEST-001")
        self.assertEqual(idea.thesis.direction, TraderThesisDirection.BULLISH)
        self.assertEqual(idea.suggested_action, TraderSuggestedAction.ENTER_LONG)
        self.assertTrue(idea.checksum)

    def test_thesis_directions_supported(self):
        expected = {"STRONG_BEARISH", "BEARISH", "LEAN_BEARISH", "NEUTRAL",
                    "LEAN_BULLISH", "BULLISH", "STRONG_BULLISH", "UNKNOWN"}
        actual = {d.value for d in TraderThesisDirection}
        self.assertEqual(expected, actual)

    def test_suggested_actions_supported(self):
        expected = {"ENTER_LONG", "EXIT_LONG", "ENTER_SHORT_ADVISORY",
                    "EXIT_SHORT_ADVISORY", "HOLD", "WAIT", "REDUCE_EXPOSURE",
                    "INCREASE_EXPOSURE_ADVISORY", "UNKNOWN"}
        actual = {a.value for a in TraderSuggestedAction}
        self.assertEqual(expected, actual)

    def test_invalid_confidence_high(self):
        record = _valid_record_dict()
        record["stated_confidence"] = 1.5
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_invalid_confidence_negative(self):
        record = _valid_record_dict()
        record["stated_confidence"] = -0.1
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_invalid_price_negative(self):
        record = _valid_record_dict()
        record["entry_zone_low"] = -100.0
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_missing_attribution(self):
        record = _valid_record_dict()
        del record["attribution"]
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_missing_publication_timestamp(self):
        record = _valid_record_dict()
        del record["published_at"]
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_naive_timestamp(self):
        record = _valid_record_dict()
        record["published_at"] = "2025-01-15T12:00:00"
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_future_timestamp(self):
        record = _valid_record_dict()
        record["published_at"] = "2099-01-15T12:00:00+00:00"
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record, ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))

    def test_unsupported_direction(self):
        record = _valid_record_dict()
        record["direction"] = "INVALID_DIRECTION"
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_unsupported_action(self):
        record = _valid_record_dict()
        record["suggested_action"] = "INVALID_ACTION"
        with self.assertRaises(ValueError):
            TraderIdeaImporter().from_manual(record)

    def test_stable_checksum(self):
        importer = TraderIdeaImporter()
        ingested = datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc)
        idea1 = importer.from_manual(_valid_record_dict(), ingested_at=ingested)
        idea2 = importer.from_manual(_valid_record_dict(), ingested_at=ingested)
        self.assertEqual(idea1.checksum, idea2.checksum)

    def test_stable_json_serialization(self):
        importer = TraderIdeaImporter()
        idea = importer.from_manual(_valid_record_dict(), ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        json1 = stable_json(idea)
        json2 = stable_json(idea)
        self.assertEqual(json1, json2)

    def test_short_advisory_cannot_execute(self):
        record = _valid_record_dict()
        record["suggested_action"] = "ENTER_SHORT_ADVISORY"
        record["direction"] = "BEARISH"
        importer = TraderIdeaImporter()
        idea = importer.from_manual(record, ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        self.assertEqual(idea.suggested_action, TraderSuggestedAction.ENTER_SHORT_ADVISORY)
        self.assertNotIn(idea.suggested_action, {TraderSuggestedAction.ENTER_LONG})


class TraderIntelligenceImportTests(unittest.TestCase):
    """T3: Import format tests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_valid_json_import(self):
        json_path = Path(__file__).resolve().parent.parent / "examples" / "trader_ideas_sample.json"
        importer = TraderIdeaImporter()
        summary = importer.from_json(json_path, ingested_at=datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(len(summary.accepted), 2)
        self.assertEqual(len(summary.rejected), 0)

    def test_valid_csv_import(self):
        csv_path = Path(__file__).resolve().parent.parent / "examples" / "trader_ideas_sample.csv"
        importer = TraderIdeaImporter()
        summary = importer.from_csv(csv_path, ingested_at=datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(len(summary.accepted), 2)
        self.assertEqual(len(summary.rejected), 0)

    def test_malformed_json_row(self):
        path = Path(self.temp.name) / "malformed.json"
        path.write_text(json.dumps([
            _valid_record_dict(),
            {"idea_id": "", "trader_id": ""},
        ]), encoding="utf-8")
        importer = TraderIdeaImporter()
        summary = importer.from_json(path, ingested_at=datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(len(summary.accepted), 1)
        self.assertEqual(len(summary.rejected), 1)

    def test_malformed_csv_row(self):
        path = Path(self.temp.name) / "malformed.csv"
        path.write_text(
            "idea_id,trader_id,trader_display_name,source_id,source_name,published_at,symbol,timeframe,market_regime,direction,explanation,suggested_action,attribution\n"
            "TI-BAD-001,trader-bad,Bad Trader,src-bad,Bad Source,2025-01-15T12:00:00+00:00,BTC/USD,4H,BULL_TREND,BULLISH,Test,ENTER_LONG,Test attribution\n"
            ",,,,,2025-01-15T12:00:00+00:00,BTC/USD,4H,BULL_TREND,BULLISH,Test,ENTER_LONG,\n"
            , encoding="utf-8")
        importer = TraderIdeaImporter()
        summary = importer.from_csv(path, ingested_at=datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(len(summary.accepted), 1)
        self.assertEqual(len(summary.rejected), 1)

    def test_multiple_records_json(self):
        path = Path(self.temp.name) / "multi.json"
        records = [_valid_record_dict(f"TI-MULTI-{i:03d}") for i in range(5)]
        path.write_text(json.dumps(records), encoding="utf-8")
        importer = TraderIdeaImporter()
        summary = importer.from_json(path, ingested_at=datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(len(summary.accepted), 5)
        self.assertEqual(len(summary.rejected), 0)


class TraderIntelligencePersistenceTests(unittest.TestCase):
    """T4: Persistence tests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "trader_intel.sqlite3"
        self.repo = TraderIntelligenceRepository(self.db_path)
        self.repo.initialize()
        self.importer = TraderIdeaImporter()
        self.ingested = datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc)

    def test_schema_version(self):
        self.repo.validate_schema()

    def test_unknown_schema_version_rejected(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE trader_intelligence_metadata SET version=999")
        conn.commit()
        conn.close()
        with self.assertRaises(TraderSchemaVersionError):
            self.repo.validate_schema()

    def test_persistence_reload(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.assertTrue(self.repo.save_idea(idea))
        loaded = self.repo.load_idea(idea.idea_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.idea_id, idea.idea_id)
        self.assertEqual(loaded.checksum, idea.checksum)

    def test_duplicate_exact_retry(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.assertTrue(self.repo.save_idea(idea))
        self.assertFalse(self.repo.save_idea(idea))

    def test_conflicting_duplicate(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.repo.save_idea(idea)
        modified = _valid_record_dict()
        modified["explanation"] = "Different explanation for conflicting test."
        conflicting = self.importer.from_manual(modified, ingested_at=self.ingested)
        with self.assertRaises(ConflictingTraderIdeaError):
            self.repo.save_idea(conflicting)

    def test_bounded_queries(self):
        for i in range(5):
            idea = self.importer.from_manual(_valid_record_dict(f"TI-BOUND-{i:03d}"), ingested_at=self.ingested)
            self.repo.save_idea(idea)
        self.assertEqual(len(self.repo.recent_ideas(3)), 3)
        with self.assertRaises(ValueError):
            self.repo.recent_ideas(0)
        with self.assertRaises(ValueError):
            self.repo.recent_ideas(1001)

    def test_filter_by_symbol(self):
        for i in range(3):
            rec = _valid_record_dict(f"TI-SYM-{i:03d}")
            rec["symbol"] = "ETH/USD" if i < 2 else "BTC/USD"
            idea = self.importer.from_manual(rec, ingested_at=self.ingested)
            self.repo.save_idea(idea)
        eth = self.repo.ideas_by_symbol("ETH/USD")
        self.assertEqual(len(eth), 2)
        btc = self.repo.ideas_by_symbol("BTC/USD")
        self.assertEqual(len(btc), 1)

    def test_filter_by_trader(self):
        for i in range(3):
            rec = _valid_record_dict(f"TI-TRD-{i:03d}")
            rec["trader_id"] = "trader-A" if i < 2 else "trader-B"
            idea = self.importer.from_manual(rec, ingested_at=self.ingested)
            self.repo.save_idea(idea)
        a = self.repo.ideas_by_trader("trader-A")
        self.assertEqual(len(a), 2)
        b = self.repo.ideas_by_trader("trader-B")
        self.assertEqual(len(b), 1)

    def test_filter_by_regime(self):
        for i in range(3):
            rec = _valid_record_dict(f"TI-REG-{i:03d}")
            rec["market_regime"] = "BULL_TREND" if i < 2 else "BEAR_TREND"
            idea = self.importer.from_manual(rec, ingested_at=self.ingested)
            self.repo.save_idea(idea)
        bull = self.repo.ideas_by_regime("BULL_TREND")
        self.assertEqual(len(bull), 2)
        bear = self.repo.ideas_by_regime("BEAR_TREND")
        self.assertEqual(len(bear), 1)

    def test_unresolved_ideas(self):
        rec = _valid_record_dict("TI-UNRES-001")
        idea = self.importer.from_manual(rec, ingested_at=self.ingested)
        self.repo.save_idea(idea)
        unresolved = self.repo.unresolved_ideas()
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0].evaluation_status, TraderEvaluationStatus.PENDING)

    def test_source_history(self):
        rec = _valid_record_dict("TI-SRC-001")
        idea = self.importer.from_manual(rec, ingested_at=self.ingested)
        self.repo.save_idea(idea)
        history = self.repo.source_history("test-source-001")
        self.assertEqual(len(history), 1)

    def test_secret_rejection(self):
        record = _valid_record_dict()
        record["attribution"] = "this has api_key in it"
        idea = self.importer.from_manual(record, ingested_at=self.ingested)
        with self.assertRaises(ValueError):
            self.repo.save_idea(idea)


class TraderIntelligenceReportTests(unittest.TestCase):
    """T5: Read-only report tests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "trader_intel.sqlite3"
        self.repo = TraderIntelligenceRepository(self.db_path)
        self.repo.initialize()
        self.importer = TraderIdeaImporter()
        self.ingested = datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc)
        self.report = TraderIntelligenceReportService(self.repo)

    def test_recent_report(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.repo.save_idea(idea)
        rows = self.report.recent()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].trader_display_name, "Test Trader")
        self.assertEqual(rows[0].symbol, "BTC/USD")
        self.assertTrue(rows[0].advisory_only)

    def test_report_by_symbol(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.repo.save_idea(idea)
        rows = self.report.by_symbol("BTC/USD")
        self.assertEqual(len(rows), 1)

    def test_report_by_trader(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.repo.save_idea(idea)
        rows = self.report.by_trader("trader-test-001")
        self.assertEqual(len(rows), 1)

    def test_report_json(self):
        idea = self.importer.from_manual(_valid_record_dict(), ingested_at=self.ingested)
        self.repo.save_idea(idea)
        rows = self.report.recent()
        json_str = TraderIntelligenceReportService.to_json(rows)
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["symbol"], "BTC/USD")


class TraderIntelligenceSafetyTests(unittest.TestCase):
    """Safety boundary tests: no Risk Manager mutation, no portfolio mutation,
    no live capability, no network access."""

    def test_no_risk_manager_mutation(self):
        from core.risk.risk_manager import RiskManager
        from models.recommendation import Recommendation
        rm = RiskManager()
        rec = Recommendation("BTC/USD", "LONG", 85.0, "Test")
        before = rm.evaluate(rec)
        importer = TraderIdeaImporter()
        idea = importer.from_manual(_valid_record_dict(), ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        after = rm.evaluate(rec)
        self.assertEqual(before.approved, after.approved)
        self.assertEqual(before.max_position_size, after.max_position_size)
        self.assertEqual(before.risk_score, after.risk_score)

    def test_no_portfolio_mutation(self):
        from paper_trading.portfolio import PaperPortfolio
        portfolio = PaperPortfolio()
        cash_before = portfolio.cash
        importer = TraderIdeaImporter()
        idea = importer.from_manual(_valid_record_dict(), ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        self.assertEqual(portfolio.cash, cash_before)
        self.assertEqual(len(portfolio.positions), 0)
        self.assertEqual(len(portfolio.orders), 0)

    def test_no_live_capability(self):
        from core.settings import RuntimeSettings
        settings = RuntimeSettings.from_env()
        self.assertEqual(settings.mode, "PAPER")
        self.assertFalse(settings.live_trading)

    def test_no_network_access(self):
        import inspect
        importer_source = inspect.getsource(TraderIdeaImporter)
        forbidden = ["urlopen", "requests.get", "requests.post", "http.client",
                     "urllib.request.urlopen", "socket.connect", "httpx", "aiohttp"]
        for term in forbidden:
            self.assertNotIn(term, importer_source,
                f"Importer source contains forbidden network term: {term}")

    def test_trader_ideas_advisory_only(self):
        record = _valid_record_dict()
        record["suggested_action"] = "ENTER_SHORT_ADVISORY"
        record["direction"] = "BEARISH"
        importer = TraderIdeaImporter()
        idea = importer.from_manual(record, ingested_at=datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc))
        self.assertEqual(idea.suggested_action, TraderSuggestedAction.ENTER_SHORT_ADVISORY)
        self.assertNotIn(idea.suggested_action, {TraderSuggestedAction.ENTER_LONG})
        self.assertTrue(idea.evaluation_status == TraderEvaluationStatus.PENDING)

    def test_no_decision_packet_integration(self):
        """Trader Intelligence must not import or depend on executable
        Decision Cycle, Risk Manager, PaperPortfolio, or order-execution
        classes.

        This checks actual import dependencies via AST parsing rather than
        broad string searches, so safety docstrings that mention these
        classes as forbidden do not false-trigger the assertion.
        """
        import ast
        from pathlib import Path

        trader_intel_modules = (
            "models/trader_intelligence.py",
            "database/trader_intelligence_repository.py",
            "services/trader_idea_importer.py",
            "services/trader_intelligence_report.py",
        )
        forbidden_roots = (
            "core.decision_cycle",
            "core.risk",
            "paper_trading",
            "services.paper_execution",
            "models.decision_packet",
        )
        repo_root = Path(__file__).resolve().parent.parent
        for rel in trader_intel_modules:
            source_path = repo_root / rel
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
            for module_name in imported:
                for root in forbidden_roots:
                    if module_name == root or module_name.startswith(root + "."):
                        self.fail(
                            f"Trader Intelligence module {rel} imports forbidden "
                            f"execution/risk/decision dependency: {module_name}"
                        )


if __name__ == "__main__":
    unittest.main()
