"""JSON CLI for local paper-mode operations."""
import argparse
from dataclasses import asdict
import json
from database.maintenance import verify_database
from database.journal import SQLiteAuditJournal
from reports.operator_reports import OperatorReports
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("database"); parser.add_argument("report",choices=("status","cycle","evidence","portfolio","positions","trades","pnl","rejections","risk","provider","alerts","integrity")); args=parser.parse_args()
    if args.report=="integrity":
        print(json.dumps(asdict(verify_database(args.database)),indent=2,sort_keys=True)); return
    journal=SQLiteAuditJournal(args.database); journal.validate_schema(); reports=OperatorReports(journal)
    functions={"status":reports.system_status,"cycle":reports.latest_decision_cycle,"evidence":reports.latest_evidence_summary,"portfolio":reports.current_paper_portfolio,"positions":reports.open_positions,"trades":reports.completed_trades,"pnl":reports.daily_pnl,"rejections":reports.rejected_decisions,"risk":reports.risk_state,"provider":reports.provider_health,"alerts":reports.alerts}
    print(reports.to_json(functions[args.report]()))
if __name__=="__main__": main()
