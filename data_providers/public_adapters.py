"""Unauthenticated, read-only public candle adapters and deterministic failover."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from data_providers.market_data import MarketDataError, ProviderHealth, normalize_symbol

class RateLimitError(MarketDataError): pass

@dataclass(frozen=True)
class PublicCandle:
    provider:str; symbol:str; timeframe:str; timestamp:datetime; close:float; volume:float|None

class PublicJsonTransport:
    def get(self,url,timeout):
        try:
            with urlopen(Request(url,headers={"User-Agent":"Hermes-OS-public-data"}),timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code==429: raise RateLimitError("Public provider rate limited the request.") from exc
            raise MarketDataError(f"Public provider HTTP error {exc.code}.") from exc
        except (URLError,TimeoutError,OSError,json.JSONDecodeError) as exc: raise MarketDataError("Public provider request failed.") from exc

class PublicCandleAdapter:
    name="public"; base_url=""
    def __init__(self,transport=None,clock=None,timeout=5.0,retries=2,max_age_seconds=18000):
        self.transport=transport or PublicJsonTransport(); self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.timeout=timeout; self.retries=retries; self.max_age_seconds=max_age_seconds; self.health=ProviderHealth(True,"READY",0)
    def get_candle(self,symbol,timeframe="4H"):
        normalized=normalize_symbol(symbol); error=None
        for attempt in range(1,self.retries+2):
            try:
                candle=self._parse(self.transport.get(self._url(normalized,timeframe),self.timeout),normalized,timeframe)
                self._validate(candle,normalized); self.health=ProviderHealth(True,"HEALTHY",attempt); return candle
            except (MarketDataError,TimeoutError,OSError,TypeError,ValueError,KeyError,IndexError,StopIteration) as exc:
                error=exc
                if attempt<=self.retries: sleep(0)
        self.health=ProviderHealth(False,"UNAVAILABLE",self.retries+1,str(error)); raise MarketDataError(f"{self.name} unavailable: {error}") from error
    def _validate(self,candle,symbol):
        if candle.symbol!=symbol: raise MarketDataError("Provider returned an inconsistent symbol.")
        if candle.timestamp.tzinfo is None: raise MarketDataError("Provider timestamp must be timezone-aware.")
        age=(self.clock().astimezone(timezone.utc)-candle.timestamp.astimezone(timezone.utc)).total_seconds()
        if age < -60: raise MarketDataError("Provider timestamp is in the future.")
        if age > self.max_age_seconds: raise MarketDataError("Provider candle is stale.")
        if candle.close<=0: raise MarketDataError("Provider price must be positive.")
    def _url(self,symbol,timeframe): raise NotImplementedError
    def _parse(self,payload,symbol,timeframe): raise NotImplementedError

class BinanceUSPublicAdapter(PublicCandleAdapter):
    name="Binance.US"; base_url="https://api.binance.us/api/v3/klines"
    def _url(self,symbol,timeframe): return self.base_url+"?"+urlencode({"symbol":symbol.replace("/",""),"interval":"4h","limit":1})
    def _parse(self,payload,symbol,timeframe):
        row=payload[0]; return PublicCandle(self.name,symbol,timeframe,datetime.fromtimestamp(int(row[0])/1000,timezone.utc),float(row[4]),float(row[5]))

class CoinbasePublicAdapter(PublicCandleAdapter):
    name="Coinbase"; base_url="https://api.exchange.coinbase.com/products"
    def _url(self,symbol,timeframe): return f"{self.base_url}/{symbol.replace('/','-')}/candles?granularity=14400"
    def _parse(self,payload,symbol,timeframe):
        row=payload[0]; return PublicCandle(self.name,symbol,timeframe,datetime.fromtimestamp(int(row[0]),timezone.utc),float(row[4]),float(row[5]))

class KrakenPublicAdapter(PublicCandleAdapter):
    name="Kraken"; base_url="https://api.kraken.com/0/public/OHLC"
    def _url(self,symbol,timeframe):
        pair=symbol.replace("BTC","XBT").replace("/",""); return self.base_url+"?"+urlencode({"pair":pair,"interval":240})
    def _parse(self,payload,symbol,timeframe):
        if payload.get("error"): raise MarketDataError("Kraken returned an error.")
        rows=next(value for key,value in payload["result"].items() if key!="last"); row=rows[-1]
        return PublicCandle(self.name,symbol,timeframe,datetime.fromtimestamp(int(row[0]),timezone.utc),float(row[4]),float(row[6]))

@dataclass(frozen=True)
class ProviderComparison:
    candles:tuple; price_spread_percent:float; timestamp_spread_seconds:float
    stale_providers:tuple[str,...]; unhealthy_providers:tuple[str,...]; selected_source:str|None; reason:str

class PublicProviderGroup:
    def __init__(self,providers): self.providers=tuple(providers)
    def compare(self,symbol,timeframe="4H"):
        candles=[]; unhealthy=[]
        for provider in self.providers:
            try: candles.append(provider.get_candle(symbol,timeframe))
            except MarketDataError: unhealthy.append(provider.name)
        if not candles: return ProviderComparison((),0,0,(),tuple(unhealthy),None,"All public providers are unavailable.")
        prices=[item.close for item in candles]; times=[item.timestamp.timestamp() for item in candles]
        spread=(max(prices)-min(prices))/min(prices)*100 if len(prices)>1 else 0
        selected=min(candles,key=lambda item:(abs(item.close-sum(prices)/len(prices)),item.provider))
        return ProviderComparison(tuple(candles),round(spread,4),max(times)-min(times),(),tuple(unhealthy),selected.provider,"Selected healthy source closest to the provider mean.")
    def get_candle(self,symbol,timeframe="4H"):
        report=self.compare(symbol,timeframe)
        if report.selected_source is None: raise MarketDataError(report.reason)
        return next(item for item in report.candles if item.provider==report.selected_source)
