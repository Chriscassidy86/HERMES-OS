"""Local audit-journal commands; outputs JSON and never accesses a network."""
import argparse, json
from database.journal import SQLiteAuditJournal
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("database")
    parser.add_argument("command",choices=("init","cycles","trades","portfolio","rejections")); args=parser.parse_args()
    journal=SQLiteAuditJournal(args.database)
    if args.command=="init": journal.initialize(); value={"initialized":True}
    else:
        journal.validate_schema(); value={"cycles":journal.recent_cycles,"trades":journal.paper_trades,"portfolio":journal.current_portfolio,"rejections":journal.rejection_history}[args.command]()
    print(json.dumps(value,indent=2,sort_keys=True))
if __name__=="__main__": main()
