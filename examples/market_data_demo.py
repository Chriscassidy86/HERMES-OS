from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from data_providers.market_data import FixtureMarketDataProvider,SnapshotBuilder
now=datetime.now(timezone.utc)
data={"symbol":"BTCUSD","price":108000,"volume_24h":42_500_000_000,"market_trend":"Bullish","volatility":2.8,"fear_greed_index":74,"timestamp":now,"previous_price":106000,"average_volume":35_000_000_000,"short_moving_average":107500,"long_moving_average":104000}
provider=FixtureMarketDataProvider({"BTC/USD":data},SnapshotBuilder(lambda:now))
print("PAPER MODE ONLY"); print(provider.get_snapshot("btcusd").summary()); print("Provider health:",provider.health.status); print("Network used: False")
