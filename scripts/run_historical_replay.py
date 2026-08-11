"""Import historical CSV candles and run the deterministic replay engine."""
import argparse
from pathlib import Path

from backtests.historical_import import HistoricalCsvCandleLoader
from backtests.replay import FixtureCandleLoader,ReplayConfig,ReplaySession

def parse_args():
    parser=argparse.ArgumentParser(description="Import historical OHLCV candles and run a replay session.")
    parser.add_argument("csv_path",help="Path to a historical OHLCV CSV file.")
    parser.add_argument("--symbol",help="Symbol to import when the CSV contains multiple markets.")
    parser.add_argument("--timeframe",default="4H",help="Replay timeframe label to attach when the CSV omits one.")
    parser.add_argument("--short-window",type=int,default=4,help="Rolling window for the short moving average.")
    parser.add_argument("--long-window",type=int,default=16,help="Rolling window for the long moving average.")
    parser.add_argument("--volume-window",type=int,default=20,help="Rolling window for the average volume.")
    parser.add_argument("--starting-balance",type=float,default=10000.0,help="Replay starting balance.")
    parser.add_argument("--fee-bps",type=float,default=10.0,help="Replay fee basis points.")
    parser.add_argument("--slippage-bps",type=float,default=5.0,help="Replay slippage basis points.")
    parser.add_argument("--export",help="Optional directory to export the replay results.")
    return parser.parse_args()

def main():
    args=parse_args()
    loader=HistoricalCsvCandleLoader(args.csv_path,symbol=args.symbol,timeframe=args.timeframe,short_window=args.short_window,long_window=args.long_window,volume_window=args.volume_window)
    candles=loader.load()
    result=ReplaySession(FixtureCandleLoader(candles),ReplayConfig(starting_balance=args.starting_balance,fee_bps=args.fee_bps,slippage_bps=args.slippage_bps)).run()
    if args.export: ReplaySession.export(result,args.export)
    print(f"Imported {len(candles)} candles from {Path(args.csv_path)}.")
    print(f"Replay decisions: {len(result.decisions)}")
    print(f"Trades: {result.metrics.trade_count} | No-trade decisions: {result.no_trade_count} | Risk rejections: {result.risk_rejections}")
    print(f"Total return: {result.metrics.total_return}% | Benchmark: {result.benchmark_return}%")
    print(f"Equity history: {result.equity_history}")
    if args.export: print(f"Exported replay artifacts to {Path(args.export)}.")
    return 0

if __name__=="__main__": raise SystemExit(main())
