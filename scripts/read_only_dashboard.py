"""Serve the CEO dashboard on localhost with GET-only routes."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from database.journal import SQLiteAuditJournal
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.ceo_dashboard import CEODashboardService
from services.command_center import CommandCenterService

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("database"); parser.add_argument("--port",type=int,default=8765); args=parser.parse_args()
    journal=SQLiteAuditJournal(args.database); journal.validate_schema()
    provider=lambda:CEODashboardService(CommandCenterService(journal)).build()
    server=ReadOnlyDashboardApplication(provider).serve("127.0.0.1",args.port)
    print(f"PAPER MODE ONLY dashboard: http://127.0.0.1:{args.port}/dashboard",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())

