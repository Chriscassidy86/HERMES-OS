"""Unauthenticated, read-only public OHLCV adapters and deterministic failover.

This module has no authentication and no trading capability.
It provides:
- single-candle access through get_candle()
- historical OHLCV access through get_candles()
- deterministic provider comparison/failover
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from data_providers.market_data import (
    MarketDataError,
    ProviderHealth,
    normalize_symbol,
)


class RateLimitError(MarketDataError):
    """Raised when a public provider explicitly rate-limits a request."""


@dataclass(frozen=True)
class PublicCandle:
    """One OHLCV candle returned by a public provider."""

    provider: str
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


class PublicJsonTransport:
    """Minimal read-only JSON transport."""

    def get(self, url, timeout):
        try:
            with urlopen(
                Request(
                    url,
                    headers={"User-Agent": "Hermes-OS-public-data"},
                ),
                timeout=timeout,
            ) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as exc:
            if exc.code == 429:
                raise RateLimitError(
                    "Public provider rate limited the request."
                ) from exc

            raise MarketDataError(
                f"Public provider HTTP error {exc.code}."
            ) from exc

        except (
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise MarketDataError(
                "Public provider request failed."
            ) from exc


class PublicCandleAdapter:
    """Base read-only public OHLCV adapter."""

    name = "public"
    base_url = ""
    max_history_limit = 1000

    def __init__(
        self,
        transport=None,
        clock=None,
        timeout=5.0,
        retries=2,
        max_age_seconds=18000,
    ):
        self.transport = transport or PublicJsonTransport()
        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        self.timeout = timeout
        self.retries = retries
        self.max_age_seconds = max_age_seconds

        self.health = ProviderHealth(
            True,
            "READY",
            0,
        )

    def get_candle(self, symbol, timeframe="4H"):
        """Return the newest available candle.

        Kept for backwards compatibility with the original Hermes API.
        """
        candles = self.get_candles(
            symbol,
            timeframe,
            limit=1,
        )

        if not candles:
            raise MarketDataError(
                f"{self.name} returned no candles."
            )

        return candles[-1]

    def get_candles(
        self,
        symbol,
        timeframe="4H",
        limit=100,
    ):
        """Return historical OHLCV candles in ascending timestamp order."""
        normalized = normalize_symbol(symbol)

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= self.max_history_limit
        ):
            raise ValueError(
                f"{self.name} candle limit must be between "
                f"1 and {self.max_history_limit}."
            )

        error = None

        for attempt in range(1, self.retries + 2):
            try:
                payload = self.transport.get(
                    self._url(
                        normalized,
                        timeframe,
                        limit,
                    ),
                    self.timeout,
                )

                candles = self._parse_many(
                    payload,
                    normalized,
                    timeframe,
                )

                if not candles:
                    raise MarketDataError(
                        f"{self.name} returned no candles."
                    )

                candles = tuple(
                    sorted(
                        candles,
                        key=lambda item: item.timestamp,
                    )
                )

                for candle in candles[:-1]:
                    self._validate_structure(
                        candle,
                        normalized,
                    )

                self._validate(
                    candles[-1],
                    normalized,
                )

                self.health = ProviderHealth(
                    True,
                    "HEALTHY",
                    attempt,
                )

                return candles

            except (
                MarketDataError,
                TimeoutError,
                OSError,
                TypeError,
                ValueError,
                KeyError,
                IndexError,
                StopIteration,
            ) as exc:
                error = exc

                if attempt <= self.retries:
                    sleep(0)

        self.health = ProviderHealth(
            False,
            "UNAVAILABLE",
            self.retries + 1,
            str(error),
        )

        raise MarketDataError(
            f"{self.name} unavailable: {error}"
        ) from error

    def _validate_structure(self, candle, symbol):
        """Validate candle shape/values without requiring freshness."""
        if candle.symbol != symbol:
            raise MarketDataError(
                "Provider returned an inconsistent symbol."
            )

        if (
            not isinstance(candle.timestamp, datetime)
            or candle.timestamp.tzinfo is None
        ):
            raise MarketDataError(
                "Provider timestamp must be timezone-aware."
            )

        values = (
            ("open", candle.open),
            ("high", candle.high),
            ("low", candle.low),
            ("close", candle.close),
        )

        for name, value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                raise MarketDataError(
                    f"Provider {name} price is invalid."
                )

            if value <= 0:
                raise MarketDataError(
                    f"Provider {name} price must be positive."
                )

        if candle.high < candle.low:
            raise MarketDataError(
                "Provider candle high is below low."
            )

        if not (
            candle.low <= candle.open <= candle.high
            and candle.low <= candle.close <= candle.high
        ):
            raise MarketDataError(
                "Provider OHLC values are internally inconsistent."
            )

        if candle.volume is not None:
            if (
                isinstance(candle.volume, bool)
                or not isinstance(candle.volume, (int, float))
                or candle.volume < 0
            ):
                raise MarketDataError(
                    "Provider volume must be non-negative."
                )

    def _validate(self, candle, symbol):
        """Validate the newest candle, including freshness."""
        self._validate_structure(candle, symbol)

        age = (
            self.clock().astimezone(timezone.utc)
            - candle.timestamp.astimezone(timezone.utc)
        ).total_seconds()

        if age < -60:
            raise MarketDataError(
                "Provider timestamp is in the future."
            )

        if age > self.max_age_seconds:
            raise MarketDataError(
                "Provider candle is stale."
            )

    def _url(self, symbol, timeframe, limit):
        raise NotImplementedError

    def _parse_many(self, payload, symbol, timeframe):
        raise NotImplementedError


class BinanceUSPublicAdapter(PublicCandleAdapter):
    name = "Binance.US"
    base_url = "https://api.binance.us/api/v3/klines"
    max_history_limit = 1000

    @staticmethod
    def _interval(timeframe):
        mapping = {
            "1M": "1m",
            "3M": "3m",
            "5M": "5m",
            "15M": "15m",
            "30M": "30m",
            "1H": "1h",
            "2H": "2h",
            "4H": "4h",
            "6H": "6h",
            "8H": "8h",
            "12H": "12h",
            "1D": "1d",
            "3D": "3d",
            "1W": "1w",
        }

        key = str(timeframe).strip().upper()

        if key not in mapping:
            raise ValueError(
                f"Unsupported Binance.US timeframe: {timeframe}"
            )

        return mapping[key]

    def _url(self, symbol, timeframe, limit):
        return self.base_url + "?" + urlencode(
            {
                "symbol": symbol.replace("/", ""),
                "interval": self._interval(timeframe),
                "limit": limit,
            }
        )

    def _parse_many(self, payload, symbol, timeframe):
        if not isinstance(payload, list):
            raise MarketDataError(
                "Binance.US returned an invalid kline payload."
            )

        candles = []

        for row in payload:
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                raise MarketDataError(
                    "Binance.US returned a malformed kline row."
                )

            candles.append(
                PublicCandle(
                    provider=self.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(
                        int(row[0]) / 1000,
                        timezone.utc,
                    ),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )

        return tuple(candles)


class CoinbasePublicAdapter(PublicCandleAdapter):
    name = "Coinbase"
    base_url = "https://api.exchange.coinbase.com/products"
    max_history_limit = 300

    @staticmethod
    def _granularity(timeframe):
        mapping = {
            "1M": 60,
            "5M": 300,
            "15M": 900,
            "30M": 1800,
            "1H": 3600,
            "2H": 7200,
            "4H": 14400,
            "6H": 21600,
            "1D": 86400,
        }

        key = str(timeframe).strip().upper()

        if key not in mapping:
            raise ValueError(
                f"Unsupported Coinbase timeframe: {timeframe}"
            )

        return mapping[key]

    def _url(self, symbol, timeframe, limit):
        return (
            f"{self.base_url}/"
            f"{symbol.replace('/', '-')}/candles?"
            f"granularity={self._granularity(timeframe)}"
        )

    def _parse_many(self, payload, symbol, timeframe):
        if not isinstance(payload, list):
            raise MarketDataError(
                "Coinbase returned an invalid candle payload."
            )

        candles = []

        # Coinbase returns:
        # [time, low, high, open, close, volume]
        for row in payload:
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                raise MarketDataError(
                    "Coinbase returned a malformed candle row."
                )

            candles.append(
                PublicCandle(
                    provider=self.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(
                        int(row[0]),
                        timezone.utc,
                    ),
                    open=float(row[3]),
                    high=float(row[2]),
                    low=float(row[1]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )

        return tuple(candles)


class KrakenPublicAdapter(PublicCandleAdapter):
    name = "Kraken"
    base_url = "https://api.kraken.com/0/public/OHLC"
    max_history_limit = 720

    @staticmethod
    def _interval(timeframe):
        mapping = {
            "1M": 1,
            "5M": 5,
            "15M": 15,
            "30M": 30,
            "1H": 60,
            "4H": 240,
            "1D": 1440,
            "1W": 10080,
        }

        key = str(timeframe).strip().upper()

        if key not in mapping:
            raise ValueError(
                f"Unsupported Kraken timeframe: {timeframe}"
            )

        return mapping[key]

    def _url(self, symbol, timeframe, limit):
        pair = (
            symbol
            .replace("BTC", "XBT")
            .replace("/", "")
        )

        # Kraken's OHLC endpoint does not expose the same
        # explicit limit parameter as Binance.US. The pair/interval
        # request returns its recent OHLC history.
        return self.base_url + "?" + urlencode(
            {
                "pair": pair,
                "interval": self._interval(timeframe),
            }
        )

    def _parse_many(self, payload, symbol, timeframe):
        if not isinstance(payload, dict):
            raise MarketDataError(
                "Kraken returned an invalid OHLC payload."
            )

        if payload.get("error"):
            raise MarketDataError(
                "Kraken returned an error."
            )

        result = payload.get("result")

        if not isinstance(result, dict):
            raise MarketDataError(
                "Kraken returned a malformed result."
            )

        rows = [
            value
            for key, value in result.items()
            if key != "last"
        ]

        if not rows:
            raise MarketDataError(
                "Kraken returned no OHLC rows."
            )

        candles = []

        # Kraken:
        # [time, open, high, low, close, vwap, volume, count]
        for row in rows[0]:
            if not isinstance(row, (list, tuple)) or len(row) < 7:
                raise MarketDataError(
                    "Kraken returned a malformed OHLC row."
                )

            candles.append(
                PublicCandle(
                    provider=self.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(
                        int(row[0]),
                        timezone.utc,
                    ),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[6]),
                )
            )

        return tuple(candles)


@dataclass(frozen=True)
class ProviderComparison:
    candles: tuple
    price_spread_percent: float
    timestamp_spread_seconds: float
    stale_providers: tuple[str, ...]
    unhealthy_providers: tuple[str, ...]
    selected_source: str | None
    reason: str


class PublicProviderGroup:
    """Compare healthy providers and select the closest price to the mean."""

    def __init__(self, providers):
        self.providers = tuple(providers)

    def compare(self, symbol, timeframe="4H"):
        candles = []
        unhealthy = []

        for provider in self.providers:
            try:
                candles.append(
                    provider.get_candle(
                        symbol,
                        timeframe,
                    )
                )
            except MarketDataError:
                unhealthy.append(provider.name)

        if not candles:
            return ProviderComparison(
                (),
                0,
                0,
                (),
                tuple(unhealthy),
                None,
                "All public providers are unavailable.",
            )

        prices = [
            item.close
            for item in candles
        ]

        times = [
            item.timestamp.timestamp()
            for item in candles
        ]

        spread = (
            (max(prices) - min(prices))
            / min(prices)
            * 100
            if len(prices) > 1
            else 0
        )

        selected = min(
            candles,
            key=lambda item: (
                abs(
                    item.close
                    - sum(prices) / len(prices)
                ),
                item.provider,
            ),
        )

        return ProviderComparison(
            tuple(candles),
            round(spread, 4),
            max(times) - min(times),
            (),
            tuple(unhealthy),
            selected.provider,
            "Selected healthy source closest to the provider mean.",
        )

    def get_candle(self, symbol, timeframe="4H"):
        report = self.compare(
            symbol,
            timeframe,
        )

        if report.selected_source is None:
            raise MarketDataError(report.reason)

        return next(
            item
            for item in report.candles
            if item.provider == report.selected_source
        )