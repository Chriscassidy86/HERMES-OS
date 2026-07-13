from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from backtests.replay import FixtureCandleLoader,HistoricalCandle,ReplaySession
now=datetime.now(timezone.utc); prices=(100,105,103,110)
candles=tuple(HistoricalCandle("BTC/USD",now+timedelta(hours=4*i),price,1500,1000,2,"Bullish",prices[i-1] if i else 98,price*1.01,price*.99) for i,price in enumerate(prices))
result=ReplaySession(FixtureCandleLoader(candles)).run()
print("PAPER MODE ONLY - ARTIFICIAL FIXTURE"); print("Trades:",result.strategy.sample_size,"Total P&L:",result.strategy.total_pnl,"Max drawdown:",result.strategy.maximum_drawdown); print("Benchmark return %:",result.benchmark_return); print("This fixture is not evidence of profitability.")
