"""Read-only command-line reports for PAPER validation artifacts."""
import argparse,json
from dataclasses import asdict
from datetime import datetime,timezone
from database.validation_repository import ValidationRepository
from services.specialist_scoreboard import SpecialistScoreboardService
def main():
 parser=argparse.ArgumentParser(); parser.add_argument("database"); parser.add_argument("report",choices=("report","scoreboard","decisions","summary")); args=parser.parse_args(); repo=ValidationRepository(args.database); repo.initialize()
 if args.report=="report": rows=repo.report_cards(1); value=asdict(rows[0]) if rows else None
 elif args.report=="scoreboard": value=asdict(SpecialistScoreboardService().build(repo.report_cards(500),as_of=datetime.now(timezone.utc)))
 elif args.report=="decisions": value=[asdict(x) for x in repo.decision_quality(100)]
 else: value=[asdict(x) for x in repo.session_summaries(10)]
 print(json.dumps(value,sort_keys=True,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
