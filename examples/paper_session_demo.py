from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from database.journal import SQLiteAuditJournal
from data_providers.market_data import FixtureMarketDataProvider,SnapshotBuilder
from paper_trading.portfolio import PaperPortfolio
from services.paper_session import PaperTradingSession
now=datetime.now(timezone.utc); data={"symbol":"BTC/USD","price":108000,"volume_24h":42_500_000_000,"market_trend":"Bullish","volatility":2.8,"fear_greed_index":74,"timestamp":now,"previous_price":106000,"average_volume":35_000_000_000,"short_moving_average":107500,"long_moving_average":104000}
provider=FixtureMarketDataProvider({"BTC/USD":data},SnapshotBuilder(lambda:now)); journal=SQLiteAuditJournal(ROOT/"data"/"paper_session.sqlite3"); journal.initialize()
result=PaperTradingSession(provider,PaperPortfolio(clock=lambda:now),journal,lambda:now).run_cycle("BTC/USD")
print("PAPER MODE ONLY"); print("Status:",result.status); print("Cycle:",result.cycle_id); print("Health:",dict(result.health)); print("Exchange contacted: False")
