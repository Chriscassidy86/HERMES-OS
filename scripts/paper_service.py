"""Continuous multi-symbol public-data PAPER service."""
from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parent.parent;sys.path.append(str(ROOT))
from core.health import GracefulShutdown
from core.settings import RuntimeSettings
from data_providers.public_adapters import BinanceUSPublicAdapter,CoinbasePublicAdapter,KrakenPublicAdapter
from database.journal import SQLiteAuditJournal
from models.multi_symbol import SymbolSchedule
from paper_trading.portfolio import PaperPortfolio
from services.multi_symbol_scheduler import MultiSymbolScheduler
from services.paper_session import PaperTradingSession
from services.provider_redundancy import RedundantPublicProvider
from services.public_snapshot_provider import PublicSnapshotProvider
from database.validation_repository import ValidationRepository
from services.paper_validation_coordinator import PaperValidationCoordinator
from services.wall_clock_soak import WallClockSoakService
from services.wall_clock_soak_observer import WallClockSoakObserver

DEFAULT_SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT")
def main():
 settings=RuntimeSettings.from_env(); journal=SQLiteAuditJournal(settings.database_path); journal.initialize()
 validation=ValidationRepository(settings.database_path); validation.initialize()
 symbols=tuple(item.strip().upper() for item in os.environ.get("HERMES_SYMBOLS",",".join(DEFAULT_SYMBOLS)).split(",") if item.strip())
 timeframe=os.environ.get("HERMES_TIMEFRAME","4H"); interval=float(os.environ.get("HERMES_CYCLE_INTERVAL_SECONDS","30"))
 redundancy=RedundantPublicProvider((BinanceUSPublicAdapter(),CoinbasePublicAdapter(),KrakenPublicAdapter()))
 provider=PublicSnapshotProvider(redundancy); shutdown=GracefulShutdown(); shutdown.install_signal_handlers()
 portfolio=PaperPortfolio(); session=PaperTradingSession(provider,portfolio,journal,provider.clock)
 coordinator=PaperValidationCoordinator(journal,validation,provider.clock)
 soak=WallClockSoakObserver(WallClockSoakService("/app/data/hermes-soak.json",clock=provider.clock,database_path=settings.database_path,log_path=settings.log_dir))
 def observe(result): coordinator.observe(result); soak.observe(result)
 scheduler=MultiSymbolScheduler(session,journal,shutdown,clock=provider.clock,observer=observe)
 print(f"HERMES PAPER MODE CONTINUOUS | symbols={','.join(symbols)} | timeframe={timeframe} | interval={interval}",flush=True)
 result=scheduler.run(tuple(SymbolSchedule(symbol) for symbol in symbols),timeframe=timeframe,interval_seconds=interval)
 print(f"HERMES PAPER MODE STOPPED | reason={result.stopped_reason} | cycles={result.cycles}",flush=True);return 0
if __name__=="__main__":raise SystemExit(main())
