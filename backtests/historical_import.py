"""Historical CSV import helpers for replay sessions."""
from csv import DictReader
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from statistics import fmean

from backtests.replay import HistoricalCandle, HistoricalCandleLoader

class HistoricalCsvCandleLoader(HistoricalCandleLoader):
    def __init__(self,path,symbol=None,timeframe="4H",short_window=4,long_window=16,volume_window=20,timestamp_column="timestamp",symbol_column="symbol",open_column="open",high_column="high",low_column="low",close_column="close",volume_column="volume",timeframe_column="timeframe"):
        self.path=Path(path)
        self.symbol=symbol
        self.timeframe=timeframe
        self.short_window=short_window
        self.long_window=long_window
        self.volume_window=volume_window
        self.timestamp_column=timestamp_column
        self.symbol_column=symbol_column
        self.open_column=open_column
        self.high_column=high_column
        self.low_column=low_column
        self.close_column=close_column
        self.volume_column=volume_column
        self.timeframe_column=timeframe_column
        if not self.path.exists(): raise FileNotFoundError(f"Historical CSV file not found: {self.path}")
        for name,value in (("short_window",short_window),("long_window",long_window),("volume_window",volume_window)):
            if not isinstance(value,int) or isinstance(value,bool) or value<1: raise ValueError(f"{name} must be a positive integer.")
    def load(self):
        rows=[]
        with self.path.open(newline="",encoding="utf-8") as handle:
            reader=DictReader(handle)
            if not reader.fieldnames: raise ValueError("Historical CSV file must include a header row.")
            required=(self.timestamp_column,self.close_column,self.high_column,self.low_column,self.volume_column)
            missing=[column for column in required if column not in reader.fieldnames]
            if missing: raise ValueError(f"Historical CSV file is missing required columns: {', '.join(missing)}.")
            for line_number,row in enumerate(reader,start=2):
                parsed=self._parse_row(row,line_number)
                if parsed is not None: rows.append(parsed)
        if not rows: raise ValueError("Historical CSV file did not contain any matching rows.")
        rows.sort(key=lambda item: item['timestamp'])
        for previous,current in zip(rows,rows[1:]):
            if current['timestamp']<=previous['timestamp']: raise ValueError("Historical CSV rows must be strictly increasing after sorting.")
        if self.symbol is None and len({row['symbol'] for row in rows})>1:
            raise ValueError("Historical CSV loader requires a symbol filter when the file contains multiple symbols.")
        candles=[]; closes=[]; volumes=[]
        for row in rows:
            previous_close=closes[-1] if closes else row['open']
            closes.append(row['close']); volumes.append(row['volume'])
            short_ma=self._rolling_average(closes,self.short_window)
            long_ma=self._rolling_average(closes,self.long_window)
            average_volume=self._rolling_average(volumes,self.volume_window)
            volatility=round(abs(row['high']-row['low'])/row['close']*100,4)
            trend='Bullish' if row['close']>previous_close else 'Bearish' if row['close']<previous_close else 'Sideways'
            candles.append(HistoricalCandle(row['symbol'],row['timestamp'],row['close'],row['volume'],average_volume,volatility,trend,previous_close,short_ma,long_ma,row['timeframe']))
        return tuple(candles)
    def _parse_row(self,row,line_number):
        symbol=self._text(row.get(self.symbol_column)) or self.symbol
        if symbol is None: raise ValueError(f"Historical CSV row {line_number} is missing a symbol.")
        if self.symbol is not None and symbol!=self.symbol: return None
        timestamp=self._parse_timestamp(self._text(row.get(self.timestamp_column)),line_number)
        open_value=self._parse_number(row.get(self.open_column),line_number,self.open_column,optional=True)
        high=self._parse_number(row.get(self.high_column),line_number,self.high_column)
        low=self._parse_number(row.get(self.low_column),line_number,self.low_column)
        close=self._parse_number(row.get(self.close_column),line_number,self.close_column)
        volume=self._parse_number(row.get(self.volume_column),line_number,self.volume_column,allow_zero=True)
        if high<low: raise ValueError(f"Historical CSV row {line_number} has high lower than low.")
        timeframe=self._text(row.get(self.timeframe_column)) or self.timeframe
        return {'symbol':symbol,'timestamp':timestamp,'open':open_value if open_value is not None else close,'high':high,'low':low,'close':close,'volume':volume,'timeframe':timeframe}
    @staticmethod
    def _text(value):
        if value is None: return None
        text=str(value).strip()
        return text or None
    @staticmethod
    def _parse_timestamp(value,line_number):
        if value is None: raise ValueError(f"Historical CSV row {line_number} is missing a timestamp.")
        try:
            numeric=float(value)
        except ValueError:
            parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        if not isfinite(numeric): raise ValueError(f"Historical CSV row {line_number} has an invalid timestamp.")
        if abs(numeric)>=1_000_000_000_000: numeric/=1000.0
        return datetime.fromtimestamp(numeric,tz=timezone.utc)
    @staticmethod
    def _parse_number(value,line_number,column,allow_zero=False,optional=False):
        text=HistoricalCsvCandleLoader._text(value)
        if text is None:
            if optional: return None
            raise ValueError(f"Historical CSV row {line_number} is missing {column}.")
        number=float(text)
        if not isfinite(number): raise ValueError(f"Historical CSV row {line_number} has an invalid {column} value.")
        if allow_zero:
            if number<0: raise ValueError(f"Historical CSV row {line_number} has a negative {column} value.")
        elif number<=0:
            raise ValueError(f"Historical CSV row {line_number} has a non-positive {column} value.")
        return number
    @staticmethod
    def _rolling_average(values,window):
        return fmean(values[-window:])
