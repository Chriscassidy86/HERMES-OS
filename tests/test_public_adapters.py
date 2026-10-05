from datetime import datetime, timezone
import unittest

from data_providers.market_data import MarketDataError
from data_providers.public_adapters import (
    BinanceUSPublicAdapter,
    CoinbasePublicAdapter,
    KrakenPublicAdapter,
    PublicProviderGroup,
)


NOW = datetime(2026, 7, 12, 12, tzinfo=timezone.utc)
TS = int(NOW.timestamp())


class Transport:
    def __init__(self, value):
        self.value = value

    def get(self, url, timeout):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def binance_row(
    price="100",
    timestamp=None,
    open_price=None,
    high=None,
    low=None,
    volume="12",
):
    close = float(price)

    if open_price is None:
        open_price = close
    if high is None:
        high = close + 1
    if low is None:
        low = close - 1

    return [[
        (timestamp or TS) * 1000,
        str(open_price),
        str(high),
        str(low),
        str(close),
        str(volume),
    ]]


def adapter(value, **kwargs):
    return BinanceUSPublicAdapter(
        Transport(value),
        lambda: NOW,
        retries=0,
        **kwargs,
    )


class PublicAdapterTests(unittest.TestCase):

    def test_valid_normalization(self):
        candle = adapter(
            binance_row()
        ).get_candle("btcusdt")

        self.assertEqual("BTC/USD", candle.symbol)

    def test_ohlcv_values_are_parsed(self):
        candle = adapter(
            binance_row(
                price="105",
                open_price="100",
                high="110",
                low="95",
                volume="25",
            )
        ).get_candle("BTC/USD")

        self.assertEqual(100.0, candle.open)
        self.assertEqual(110.0, candle.high)
        self.assertEqual(95.0, candle.low)
        self.assertEqual(105.0, candle.close)
        self.assertEqual(25.0, candle.volume)

    def test_historical_candles_are_returned(self):
        payload = [
            [
                (TS - 7200) * 1000,
                "90",
                "105",
                "88",
                "100",
                "10",
            ],
            [
                (TS - 3600) * 1000,
                "100",
                "112",
                "97",
                "108",
                "14",
            ],
            [
                TS * 1000,
                "108",
                "115",
                "104",
                "112",
                "18",
            ],
        ]

        candles = adapter(payload).get_candles(
            "BTC/USD",
            "4H",
            limit=3,
        )

        self.assertEqual(3, len(candles))
        self.assertEqual(100.0, candles[0].close)
        self.assertEqual(112.0, candles[-1].close)

    def test_timeout(self):
        with self.assertRaises(MarketDataError):
            adapter(TimeoutError()).get_candle("BTC/USD")

    def test_malformed_response(self):
        with self.assertRaises(MarketDataError):
            adapter({}).get_candle("BTC/USD")

    def test_stale_data(self):
        with self.assertRaises(MarketDataError):
            adapter(
                binance_row(timestamp=TS - 20000)
            ).get_candle("BTC/USD")

    def test_future_data(self):
        with self.assertRaises(MarketDataError):
            adapter(
                binance_row(timestamp=TS + 120)
            ).get_candle("BTC/USD")

    def test_invalid_ohlc_relationship(self):
        with self.assertRaises(MarketDataError):
            adapter(
                binance_row(
                    open_price="120",
                    high="110",
                    low="100",
                    price="105",
                )
            ).get_candle("BTC/USD")

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            adapter(
                binance_row()
            ).get_candles(
                "BTC/USD",
                "4H",
                limit=0,
            )

    def test_inconsistent_symbol_fails_validation(self):
        item = adapter(binance_row())

        item._parse_many = (
            lambda payload, symbol, timeframe:
            (
                BinanceUSPublicAdapter(
                    Transport(payload),
                    lambda: NOW,
                    retries=0,
                )._parse_many(
                    payload,
                    "ETH/USD",
                    timeframe,
                )
            )
        )

        with self.assertRaises(MarketDataError):
            item.get_candle("BTC/USD")

    def test_provider_disagreement_report(self):
        first = adapter(
            binance_row(
                price="100",
                open_price="99",
                high="101",
                low="98",
            )
        )

        second = adapter(
            binance_row(
                price="110",
                open_price="109",
                high="111",
                low="108",
            )
        )

        report = PublicProviderGroup(
            (first, second)
        ).compare("BTC/USD")

        self.assertEqual(
            10,
            report.price_spread_percent,
        )

    def test_failover(self):
        good = adapter(
            binance_row(
                price="100",
                open_price="99",
                high="101",
                low="98",
            )
        )

        report = PublicProviderGroup(
            (
                adapter(TimeoutError()),
                good,
            )
        ).compare("BTC/USD")

        self.assertTrue(report.unhealthy_providers)
        self.assertIsNotNone(report.selected_source)

    def test_all_providers_unavailable(self):
        with self.assertRaises(MarketDataError):
            PublicProviderGroup(
                (
                    adapter(TimeoutError()),
                )
            ).get_candle("BTC/USD")

    def test_exchange_parsers_and_no_private_capability(self):
        coin = CoinbasePublicAdapter(
            Transport(
                [[
                    TS,
                    "95",
                    "110",
                    "100",
                    "101",
                    "5",
                ]]
            ),
            lambda: NOW,
            retries=0,
        )

        kraken = KrakenPublicAdapter(
            Transport(
                {
                    "error": [],
                    "result": {
                        "XXBTZUSD": [[
                            TS,
                            "95",
                            "110",
                            "90",
                            "102",
                            "0",
                            "6",
                            1,
                        ]],
                        "last": TS,
                    },
                }
            ),
            lambda: NOW,
            retries=0,
        )

        coin_candle = coin.get_candle("BTC/USD")
        kraken_candle = kraken.get_candle("BTC/USD")

        self.assertEqual(
            (101.0, 102.0),
            (
                coin_candle.close,
                kraken_candle.close,
            ),
        )

        self.assertEqual(
            (100.0, 95.0),
            (
                coin_candle.open,
                kraken_candle.open,
            ),
        )

        for value in (
            adapter(binance_row()),
            coin,
            kraken,
        ):
            self.assertFalse(
                any(
                    hasattr(value, name)
                    for name in (
                        "authenticate",
                        "create_order",
                        "place_order",
                        "api_key",
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()