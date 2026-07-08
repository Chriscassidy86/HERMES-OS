from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from reports.market_snapshot import MarketSnapshot
from agents.trend.trend_specialist import TrendSpecialist


snapshot = MarketSnapshot(
    symbol="BTC/USD",
    price=108000.25,
    volume_24h=42500000000,
    market_trend="Bullish",
    volatility=2.8,
    fear_greed_index=74,
)

specialist = TrendSpecialist()
report, signal = specialist.analyze(snapshot)

print(report.summary())
print("Valid:", report.is_valid())
print("Facts:", report.facts)
print("Warnings:", report.warnings)
print("Signal:", signal.summary())
