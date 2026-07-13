"""Foreground paper-mode supervisor. It performs health checks, not trades."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.health import GracefulShutdown,StartupChecks
from core.settings import RuntimeSettings
from database.journal import SQLiteAuditJournal

def main():
    settings=RuntimeSettings.from_env(); journal=SQLiteAuditJournal(settings.database_path); journal.initialize()
    shutdown=GracefulShutdown(); shutdown.install_signal_handlers()
    print("HERMES PAPER MODE SERVICE",flush=True)
    while not shutdown.requested:
        summary=StartupChecks(settings,journal).run()
        if not summary.healthy:
            print("UNHEALTHY",flush=True); return 1
        shutdown.wait(30)
    print("HERMES PAPER MODE SERVICE STOPPED",flush=True); return 0
if __name__=="__main__": raise SystemExit(main())
