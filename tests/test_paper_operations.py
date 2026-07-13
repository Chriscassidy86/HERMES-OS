from datetime import datetime, timezone
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.health import GracefulShutdown
from database.journal import SQLiteAuditJournal
from database.maintenance import backup_database, verify_backup, verify_database
from paper_trading.portfolio import PaperPortfolio
from services.paper_operations import PaperOperationConfig, PaperOperationsService
from services.paper_session import PaperSessionResult
from reports.operator_cli import main as operator_main


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class FakeSession:
    def __init__(self, statuses):
        self.portfolio = PaperPortfolio(clock=lambda: NOW)
        self.statuses = iter(statuses)

    def run_cycle(self, symbol, timeframe="4H"):
        status = next(self.statuses)
        return PaperSessionResult(status, symbol, None)


class FakeJournal:
    def __init__(self, recovered=False): self.recovered = recovered; self.validated = False
    def validate_schema(self): self.validated = True
    def restore_portfolio(self, _portfolio): return self.recovered


class PaperOperationsTests(unittest.TestCase):
    def test_bounded_run_recovers_and_aggregates_statuses(self):
        session = FakeSession(("NO_TRADE", "PAPER_FILLED"))
        journal = FakeJournal(True)
        service = PaperOperationsService(session, journal, GracefulShutdown(), clock=lambda: NOW,
                                         wait=lambda _seconds: False)
        result = service.run(PaperOperationConfig(("BTC/USD",), interval_seconds=0), maximum_batches=2)
        self.assertTrue(result.recovered_portfolio)
        self.assertEqual("BATCH_LIMIT_REACHED", result.stopped_reason)
        self.assertEqual((('NO_TRADE', 1), ('PAPER_FILLED', 1)), result.status_counts)
        self.assertIn(("recent_cycles", "2"), result.cycle_metrics)

    def test_batch_callback_and_memory_bound(self):
        batches = []
        service = PaperOperationsService(
            FakeSession(("NO_TRADE", "NO_TRADE", "NO_TRADE")), FakeJournal(),
            GracefulShutdown(), clock=lambda: NOW, wait=lambda _seconds: False,
            on_batch=lambda timestamp, results: batches.append((timestamp, results)),
        )
        result = service.run(PaperOperationConfig(("BTC/USD",), interval_seconds=0, recent_cycle_limit=2), maximum_batches=3)
        self.assertEqual(3, len(batches))
        self.assertIn(("recent_cycles", "2"), result.cycle_metrics)

    def test_failure_circuit_opens_after_consecutive_batch_failures(self):
        session = FakeSession(("PROVIDER_FAILURE", "PROVIDER_FAILURE", "NO_TRADE"))
        service = PaperOperationsService(session, FakeJournal(), GracefulShutdown(), clock=lambda: NOW,
                                         wait=lambda _seconds: False)
        result = service.run(PaperOperationConfig(("BTC/USD",),  interval_seconds=0,
                                                  max_consecutive_failures=2))
        self.assertEqual("FAILURE_CIRCUIT_OPEN", result.stopped_reason)
        self.assertEqual(2, result.batches_completed)

    def test_requested_shutdown_does_not_run_a_batch(self):
        shutdown = GracefulShutdown(); shutdown.request()
        result = PaperOperationsService(FakeSession(()), FakeJournal(), shutdown,
                                        clock=lambda: NOW).run(PaperOperationConfig(("BTC/USD",)))
        self.assertEqual(0, result.batches_completed)
        self.assertEqual("SHUTDOWN_REQUESTED", result.stopped_reason)

    def test_invalid_configuration_fails_closed(self):
        service = PaperOperationsService(FakeSession(()), FakeJournal(), GracefulShutdown(), clock=lambda: NOW)
        with self.assertRaises(ValueError): service.run(PaperOperationConfig(()), maximum_batches=1)
        with self.assertRaises(ValueError): service.run(PaperOperationConfig(("BTC/USD", "BTC/USD")), maximum_batches=1)
        with self.assertRaises(ValueError): service.run(PaperOperationConfig(("BTC/USD",), interval_seconds=float("nan")), maximum_batches=1)
        with self.assertRaises(ValueError): service.run(PaperOperationConfig(("BTC/USD",), recent_cycle_limit=0), maximum_batches=1)

    def test_database_and_backup_integrity_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source.sqlite3"; backup = root / "backup.sqlite3"
            SQLiteAuditJournal(source).initialize()
            self.assertTrue(verify_database(source).healthy)
            backup_database(source, backup)
            self.assertTrue(verify_backup(source, backup).matching_row_counts)

    def test_invalid_database_fails_integrity_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.sqlite3"
            with self.assertRaises(ValueError): verify_database(path)

    def test_operator_integrity_command_is_read_only_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator.sqlite3"
            SQLiteAuditJournal(path).initialize()
            output = StringIO()
            with patch("sys.argv", ["operator_cli", str(path), "integrity"]), redirect_stdout(output):
                operator_main()
            self.assertIn('"healthy": true', output.getvalue())
            self.assertEqual([], SQLiteAuditJournal(path).recent_cycles())


if __name__ == "__main__":
    unittest.main()
