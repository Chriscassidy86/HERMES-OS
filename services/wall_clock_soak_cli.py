"""Operator CLI for persistent wall-clock PAPER soak validation."""
import argparse,json
from dataclasses import asdict
from services.wall_clock_soak import WallClockSoakService
def main():
 parser=argparse.ArgumentParser(); parser.add_argument("command",choices=("start","status","stop","export")); parser.add_argument("value",nargs="?"); parser.add_argument("--state",default="data/hermes-soak.json"); parser.add_argument("--database",default="data/hermes.sqlite3"); parser.add_argument("--logs",default="logs"); args=parser.parse_args(); service=WallClockSoakService(args.state,database_path=args.database,log_path=args.logs)
 if args.command=="start": result=service.start(args.value)
 elif args.command=="status": result=service.status()
 elif args.command=="stop": result=service.stop()
 else: service.export(args.value or "data/hermes-soak-report.json"); result=service.status()
 print(json.dumps(asdict(result),sort_keys=True,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
