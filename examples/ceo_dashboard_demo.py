"""Render the read-only CEO dashboard from one persisted paper decision."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from reports.ceo_dashboard import CEODashboardRenderer
from reports.market_snapshot import MarketSnapshot
from services.ceo_dashboard import CEODashboardService
from services.command_center import CommandCenterService


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
snapshot = MarketSnapshot("BTC/USD", 102, 1500, "Bullish", 2, 55, 100, 1000, 101, 99, "4H", NOW)
with TemporaryDirectory() as directory:
    journal = SQLiteAuditJournal(Path(directory) / "dashboard.sqlite3")
    journal.initialize(); journal.save_cycle(DecisionCycle(clock=lambda: NOW).run(snapshot))
    view = CEODashboardService(CommandCenterService(journal, clock=lambda: NOW)).build()
    print(CEODashboardRenderer().to_json(view))

