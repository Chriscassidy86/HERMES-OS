"""Deterministic fail-closed redundancy for unauthenticated public candles."""
from dataclasses import replace
from time import monotonic
from datetime import datetime,timezone
from math import isfinite
from data_providers.market_data import MarketDataError,normalize_symbol
from models.provider_redundancy import AttributedPublicCandle,RedundantProviderState

class RedundantPublicProvider:
    def __init__(self,providers,*,conflict_tolerance_percent=2.0,cooldown_failures=3,cooldown_cycles=2,latency_clock=None,clock=None,max_age_seconds=18000):
        self.providers=tuple(providers); self.tolerance=conflict_tolerance_percent; self.cooldown_failures=cooldown_failures; self.cooldown_cycles=cooldown_cycles; self.latency_clock=latency_clock or monotonic; self.clock=clock or (lambda:datetime.now(timezone.utc)); self.max_age_seconds=max_age_seconds; self._states={}
        if not self.providers or len({p.name for p in self.providers})!=len(self.providers): raise ValueError("Unique public providers are required.")
        if not isfinite(self.tolerance) or self.tolerance<0 or cooldown_failures<1 or cooldown_cycles<0 or max_age_seconds<=0: raise ValueError("Provider redundancy configuration is invalid.")
    def get_candle(self,symbol,timeframe="4H"):
        normalized=normalize_symbol(symbol)
        if normalized not in {"BTC/USD","ETH/USD","SOL/USD","XRP/USD"}: raise MarketDataError("Unsupported public symbol mapping.")
        if timeframe!="4H": raise MarketDataError("Unsupported public timeframe mapping.")
        successes=[]; failovers=0
        for index,provider in enumerate(self.providers):
            key=(provider.name,normalized); state=self._states.get(key,RedundantProviderState(provider.name,normalized,0,0,0,0,0,True,1))
            if state.cooldown_remaining>0:
                self._states[key]=replace(state,cooldown_remaining=state.cooldown_remaining-1); continue
            started=self.latency_clock()
            try:
                candle=provider.get_candle(normalized,timeframe)
                latency=max(0,(self.latency_clock()-started)*1000)
                if candle.provider!=provider.name or candle.symbol!=normalized or candle.timeframe!=timeframe: raise MarketDataError("Provider attribution or compatibility mismatch.")
                if not isinstance(candle.timestamp,datetime) or candle.timestamp.tzinfo is None or not isfinite(candle.close) or candle.close<=0: raise MarketDataError("Provider candle is malformed.")
                age=(self.clock().astimezone(timezone.utc)-candle.timestamp.astimezone(timezone.utc)).total_seconds()
                if age>self.max_age_seconds: raise MarketDataError("Provider candle is stale.")
                if age < -60: raise MarketDataError("Provider candle is future-dated.")
                state=replace(state,successes=state.successes+1,consecutive_failures=0,latency_ms=round(latency,3),healthy=True,score=round((state.successes+2)/(state.successes+state.failures+2),6))
                successes.append((index,candle))
            except Exception:
                failures=state.failures+1; consecutive=state.consecutive_failures+1
                state=replace(state,failures=failures,consecutive_failures=consecutive,healthy=False,cooldown_remaining=self.cooldown_cycles if consecutive>=self.cooldown_failures else 0,score=round((state.successes+1)/(state.successes+failures+2),6))
            self._states[key]=state
        if not successes: raise MarketDataError("All public providers failed closed.")
        prices=[item.close for _,item in successes]
        if len(prices)>1 and (max(prices)-min(prices))/min(prices)*100>self.tolerance: raise MarketDataError("Public provider prices conflict beyond tolerance.")
        selected=min(successes,key=lambda item:item[0]); failovers=selected[0]
        states=tuple(self._states[(p.name,normalized)] for p in self.providers if (p.name,normalized) in self._states)
        return AttributedPublicCandle(selected[1],selected[1].provider,states,failovers)
