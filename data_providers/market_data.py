"""Validated read-only market-data abstractions; no trading capability exists here."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Protocol
from reports.market_snapshot import MarketSnapshot

class MarketDataError(RuntimeError): pass
class StaleMarketDataError(MarketDataError): pass
@dataclass(frozen=True)
class ProviderHealth:
    healthy: bool; status: str; attempts: int; last_error: str|None=None
class MarketDataProvider(Protocol):
    health: ProviderHealth
    def get_snapshot(self,symbol:str,timeframe:str="4H")->MarketSnapshot: ...

def normalize_symbol(symbol):
    value=symbol.strip().upper().replace("-","/").replace("_","/")
    if "/" not in value:
        for quote in ("USDT","USD","BTC","ETH"):
            if value.endswith(quote) and len(value)>len(quote): value=f"{value[:-len(quote)]}/{quote}"; break
    if value.endswith("/USDT"): value=value[:-5]+"/USD"
    if value.count("/")!=1 or not all(value.split("/")): raise MarketDataError("Symbol format is invalid.")
    return value

class SnapshotBuilder:
    REQUIRED=("symbol","price","volume_24h","market_trend","volatility","fear_greed_index","timestamp")
    def __init__(self,clock=None,max_age_seconds=14400): self.clock=clock or (lambda:datetime.now(timezone.utc)); self.max_age_seconds=max_age_seconds
    def build(self,data:dict[str,Any],timeframe="4H"):
        missing=[key for key in self.REQUIRED if key not in data]
        if missing: raise MarketDataError(f"Missing market fields: {', '.join(missing)}")
        timestamp=data["timestamp"]
        if not isinstance(timestamp,datetime) or timestamp.tzinfo is None: raise MarketDataError("Market timestamp must be timezone-aware.")
        age=(self.clock().astimezone(timezone.utc)-timestamp.astimezone(timezone.utc)).total_seconds()
        if age>self.max_age_seconds: raise StaleMarketDataError("Market data is stale.")
        try:
            snapshot=MarketSnapshot(symbol=normalize_symbol(data["symbol"]),price=float(data["price"]),volume_24h=float(data["volume_24h"]),
                market_trend=str(data["market_trend"]),volatility=float(data["volatility"]),fear_greed_index=int(data["fear_greed_index"]),
                previous_price=float(data["previous_price"]) if data.get("previous_price") is not None else None,
                average_volume=float(data["average_volume"]) if data.get("average_volume") is not None else None,
                short_moving_average=float(data["short_moving_average"]) if data.get("short_moving_average") is not None else None,
                long_moving_average=float(data["long_moving_average"]) if data.get("long_moving_average") is not None else None,
                timeframe=timeframe,timestamp=timestamp.astimezone(timezone.utc))
        except (TypeError,ValueError) as exc: raise MarketDataError("Market response contains malformed numeric data.") from exc
        from core.decision_cycle import DecisionCycle
        errors=DecisionCycle._validate_snapshot(snapshot)
        if errors: raise MarketDataError(" ".join(errors))
        return snapshot

class FixtureMarketDataProvider:
    def __init__(self,fixtures,builder): self.fixtures={normalize_symbol(k):v for k,v in fixtures.items()}; self.builder=builder; self.health=ProviderHealth(True,"READY",0)
    def get_snapshot(self,symbol,timeframe="4H"):
        key=normalize_symbol(symbol)
        if key not in self.fixtures:
            self.health=ProviderHealth(False,"UNAVAILABLE",1,"Fixture symbol unavailable."); raise MarketDataError(self.health.last_error)
        try: value=self.builder.build(self.fixtures[key],timeframe)
        except MarketDataError as exc: self.health=ProviderHealth(False,"INVALID",1,str(exc)); raise
        self.health=ProviderHealth(True,"HEALTHY",1); return value

class ReplayMarketDataProvider:
    def __init__(self,records:Iterable[dict],builder): self.records=tuple(records); self.builder=builder; self.index=0; self.health=ProviderHealth(True,"READY",0)
    def get_snapshot(self,symbol,timeframe="4H"):
        if self.index>=len(self.records): self.health=ProviderHealth(False,"EXHAUSTED",self.index,"Replay exhausted."); raise MarketDataError(self.health.last_error)
        record=self.records[self.index]; self.index+=1
        if normalize_symbol(record["symbol"])!=normalize_symbol(symbol): raise MarketDataError("Replay symbol mismatch.")
        value=self.builder.build(record,timeframe); self.health=ProviderHealth(True,"HEALTHY",self.index); return value

class ReadOnlyPublicMarketDataProvider:
    """Injected public fetch boundary. It exposes no authentication or order methods."""
    def __init__(self,fetch:Callable[[str,str],dict],builder,retries=2,timeout_seconds=5.0):
        self.fetch=fetch; self.builder=builder; self.retries=retries; self.timeout_seconds=timeout_seconds; self.health=ProviderHealth(True,"READY",0)
    def get_snapshot(self,symbol,timeframe="4H"):
        error=None
        for attempt in range(1,self.retries+2):
            started=monotonic()
            try:
                data=self.fetch(normalize_symbol(symbol),timeframe)
                if monotonic()-started>self.timeout_seconds: raise TimeoutError("Public provider timed out.")
                value=self.builder.build(data,timeframe); self.health=ProviderHealth(True,"HEALTHY",attempt); return value
            except (MarketDataError,TimeoutError,OSError) as exc: error=exc
        self.health=ProviderHealth(False,"UNAVAILABLE",self.retries+1,str(error)); raise MarketDataError(str(error)) from error
