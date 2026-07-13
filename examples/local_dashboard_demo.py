"""View one read-only local dashboard response without opening a server."""
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from database.journal import SQLiteAuditJournal
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.ceo_dashboard import CEODashboardService
from services.command_center import CommandCenterService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
with TemporaryDirectory() as directory:
 journal=SQLiteAuditJournal(Path(directory)/"dashboard.sqlite3"); journal.initialize()
 provider=lambda:CEODashboardService(CommandCenterService(journal,clock=lambda:NOW)).build()
 status,headers,body=ReadOnlyDashboardApplication(provider).handle("GET","/dashboard")
 print(status,headers); print(body.decode("utf-8")); print("Mutation routes available: False")

