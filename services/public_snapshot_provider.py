"""Convert attributed public candles into conservative observed snapshots."""
from datetime import datetime,timezone
from data_providers.market_data import ProviderHealth
from reports.market_snapshot import MarketSnapshot

class PublicSnapshotProvider:
    def __init__(self,redundancy,*,clock=None):
        self.redundancy=redundancy; self.clock=clock or (lambda:datetime.now(timezone.utc)); self.previous={}; self.health=ProviderHealth(True,"READY",0)
    def get_snapshot(self,symbol,timeframe="4H"):
        try: attributed=self.redundancy.get_candle(symbol,timeframe)
        except Exception as exc:
            self.health=ProviderHealth(False,"UNAVAILABLE",self.health.attempts+1,str(exc)); raise
        candle=attributed.candle; previous=self.previous.get(candle.symbol,candle.close); change=(candle.close-previous)/previous if previous else 0
        trend="Bullish" if change>.001 else ("Bearish" if change<-.001 else "Sideways")
        now=self.clock().astimezone(timezone.utc); self.previous[candle.symbol]=candle.close
        self.health=ProviderHealth(True,f"HEALTHY:{attributed.source}",self.health.attempts+1)
        return MarketSnapshot(candle.symbol,candle.close,float(candle.volume or 0),trend,abs(change),50,previous,float(candle.volume or 0),candle.close,candle.close,timeframe,now,attributed.source,candle.timestamp)
