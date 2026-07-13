"""Serve the CEO dashboard on localhost with GET-only routes."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from database.journal import SQLiteAuditJournal
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.command_center import CommandCenterService
from services.web_dashboard import WebDashboardService
from database.validation_repository import ValidationRepository
from services.validation_dashboard import ValidationDashboardService
from datetime import datetime,timezone

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("database"); parser.add_argument("--port",type=int,default=8765); parser.add_argument("--container-bridge",action="store_true"); args=parser.parse_args()
    journal=SQLiteAuditJournal(args.database); journal.validate_schema()
    validation=ValidationRepository(args.database); validation.initialize()
    provider=WebDashboardService(CommandCenterService(journal),"V6 launch").build
    host="0.0.0.0" if args.container_bridge else "127.0.0.1"
    validation_provider=ValidationDashboardService(validation,lambda:datetime.now(timezone.utc)).build
    server=ReadOnlyDashboardApplication(provider,validation_provider=validation_provider,allow_container_bridge=args.container_bridge).serve(host,args.port)
    print(f"PAPER MODE ONLY dashboard: http://{host}:{args.port}/",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())

