from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from database.journal import SQLiteAuditJournal
from reports.operator_reports import OperatorReports
with tempfile.TemporaryDirectory() as directory:
    journal=SQLiteAuditJournal(Path(directory)/"reports.sqlite3"); journal.initialize(); reports=OperatorReports(journal)
    print("PAPER MODE ONLY"); print(reports.to_json(reports.system_status())); print("Read only: True")
