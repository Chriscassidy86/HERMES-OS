from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.settings import RuntimeSettings
from core.health import StartupChecks
from database.journal import SQLiteAuditJournal
settings=RuntimeSettings.from_env()
journal=SQLiteAuditJournal(settings.database_path) if settings.database_path.exists() else None
summary=StartupChecks(settings,journal).run()
print("PAPER MODE" if summary.healthy else "UNHEALTHY"); raise SystemExit(0 if summary.healthy else 1)
