"""Run one bounded, recovery-aware paper operations batch from fixtures."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.health import GracefulShutdown
from data_providers.market_data import FixtureMarketDataProvider, SnapshotBuilder
from database.journal import SQLiteAuditJournal
from paper_trading.portfolio import PaperPortfolio
from services.paper_operations import PaperOperationConfig, PaperOperationsService
from services.paper_session import PaperTradingSession


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
DATA = {"symbol":"BTC/USD","price":102,"volume_24h":1500,"market_trend":"Bullish",
        "volatility":2,"fear_greed_index":55,"timestamp":NOW,"previous_price":100,
        "average_volume":1000,"short_moving_average":101,"long_moving_average":99}

with TemporaryDirectory() as directory:
    journal = SQLiteAuditJournal(Path(directory) / "paper.sqlite3")
    journal.initialize()
    provider = FixtureMarketDataProvider({"BTC/USD": DATA}, SnapshotBuilder(lambda: NOW))
    portfolio = PaperPortfolio(clock=lambda: NOW)
    session = PaperTradingSession(provider, portfolio, journal, lambda: NOW)
    operations = PaperOperationsService(session, journal, GracefulShutdown(), clock=lambda: NOW,
                                        wait=lambda _seconds: False)
    summary = operations.run(PaperOperationConfig(("BTC/USD",), interval_seconds=0), maximum_batches=1)
    print("PAPER MODE ONLY")
    print("Stopped:", summary.stopped_reason)
    print("Batches:", summary.batches_completed, "Statuses:", summary.status_counts)

