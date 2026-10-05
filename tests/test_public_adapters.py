from datetime import datetime, timedelta, timezone
import unittest

from data_providers.market_data import MarketDataError
from data_providers.public_adapters import (
    BinanceUSPublicAdapter,
    CoinbasePublicAdapter,
    KrakenPublicAdapter,
    PublicCandle,
    PublicProviderGroup,
)


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class Transport:
    def __init__(self, value):
        self.value = value

    def get(self, url, timeout):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


def row(
    timestamp,
    close,
    open_price=None,
    high=None,
    low=None,
    volume=1000,
):
    close = float(close)

    if open_price is None:
        open_price = close

    if high is None:
        high = max(open_price, close) + 1

    if low is None:
        low = min(open_price, close) - 1

    return [
        int(timestamp.timestamp() * 1000),
        str(open_price),
        str(high),
        str(low),
        str(close),
        str(volume),
        int(timestamp.timestamp() * 1000),
        "0",
        0,
        "0",
        "0",
        "0",
    ]


def adapter(
    value,
    *,
    now=NOW,
    retries=0,
    max_age_seconds=18000,
):
    return BinanceUSPublicAdapter(
        Transport(value),
        Clock(now),
        retries=retries,
        max_age_seconds=max_age_seconds,
    )


class PublicAdapterTests(unittest.TestCase):

    def test_valid_normalization(self):
        candle = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                )
            ]
        ).get_candle("btcusdt")

        self.assertEqual(
            "BTC/USD",
            candle.symbol,
        )

    def test_ohlcv_values_are_parsed(self):
        candle = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    close=105,
                    open_price=100,
                    high=110,
                    low=95,
                    volume=25,
                )
            ]
        ).get_candle("BTC/USD")

        self.assertEqual(100.0, candle.open)
        self.assertEqual(110.0, candle.high)
        self.assertEqual(95.0, candle.low)
        self.assertEqual(105.0, candle.close)
        self.assertEqual(25.0, candle.volume)

    def test_historical_candles_are_returned(self):
        payload = [
            row(
                NOW - timedelta(hours=12),
                100,
            ),
            row(
                NOW - timedelta(hours=8),
                108,
            ),
            row(
                NOW - timedelta(hours=4),
                112,
            ),
            row(
                NOW - timedelta(minutes=1),
                115,
            ),
        ]

        candles = adapter(payload).get_candles(
            "BTC/USD",
            "4H",
            limit=4,
        )

        self.assertEqual(
            4,
            len(candles),
        )

        self.assertEqual(
            100.0,
            candles[0].close,
        )

        self.assertEqual(
            115.0,
            candles[-1].close,
        )

        for first, second in zip(
            candles,
            candles[1:],
        ):
            self.assertLess(
                first.timestamp,
                second.timestamp,
            )

    def test_historical_candle_limit(self):
        payload = [
            row(
                NOW - timedelta(hours=12),
                100,
            ),
            row(
                NOW - timedelta(hours=8),
                105,
            ),
            row(
                NOW - timedelta(hours=4),
                110,
            ),
            row(
                NOW - timedelta(minutes=1),
                115,
            ),
        ]

        candles = PublicProviderGroup(
            (
                adapter(payload),
            )
        ).get_candles(
            "BTC/USD",
            "4H",
            limit=2,
        )

        self.assertEqual(
            2,
            len(candles),
        )

        self.assertEqual(
            110.0,
            candles[0].close,
        )

        self.assertEqual(
            115.0,
            candles[1].close,
        )

    def test_historical_limit_above_maximum_fails(self):
        with self.assertRaises(ValueError):
            PublicProviderGroup(
                (
                    adapter(
                        [
                            row(
                                NOW - timedelta(minutes=1),
                                100,
                            )
                        ]
                    ),
                )
            ).get_candles(
                "BTC/USD",
                "4H",
                limit=201,
            )

    def test_historical_limit_zero_fails(self):
        with self.assertRaises(ValueError):
            adapter(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        100,
                    )
                ]
            ).get_candles(
                "BTC/USD",
                "4H",
                limit=0,
            )

    def test_timeout(self):
        with self.assertRaises(MarketDataError):
            adapter(
                TimeoutError()
            ).get_candle("BTC/USD")

    def test_malformed_response(self):
        with self.assertRaises(MarketDataError):
            adapter({}).get_candle("BTC/USD")

    def test_stale_data(self):
        with self.assertRaises(MarketDataError):
            adapter(
                [
                    row(
                        NOW - timedelta(hours=6),
                        100,
                    )
                ],
                now=NOW,
                max_age_seconds=100,
            ).get_candle("BTC/USD")

    def test_future_data(self):
        with self.assertRaises(MarketDataError):
            adapter(
                [
                    row(
                        NOW + timedelta(seconds=120),
                        100,
                    )
                ],
                now=NOW,
            ).get_candle("BTC/USD")

    def test_invalid_ohlc_relationship(self):
        bad = [
            [
                int(
                    (NOW - timedelta(minutes=1)).timestamp()
                    * 1000
                ),
                "120",
                "110",
                "90",
                "105",
                "1000",
            ]
        ]

        with self.assertRaises(MarketDataError):
            adapter(bad).get_candle("BTC/USD")

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            adapter(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        100,
                    )
                ]
            ).get_candles(
                "BTC/USD",
                "4H",
                limit=1001,
            )

    def test_inconsistent_symbol_fails_validation(self):
        item = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                )
            ]
        )

        bad_candle = PublicCandle(
            provider="Binance.US",
            symbol="ETH/USD",
            timeframe="4H",
            timestamp=NOW - timedelta(minutes=1),
            open=99.0,
            high=101.0,
            low=98.0,
            close=100.0,
            volume=10.0,
        )

        with self.assertRaises(MarketDataError):
            item._validate(
                bad_candle,
                "BTC/USD",
            )

    def test_provider_disagreement_report(self):
        first = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                )
            ]
        )

        second = BinanceUSPublicAdapter(
            Transport(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        110,
                    )
                ]
            ),
            Clock(NOW),
            retries=0,
        )

        report = PublicProviderGroup(
            (
                first,
                second,
            )
        ).compare("BTC/USD")

        self.assertEqual(
            10,
            report.price_spread_percent,
        )

        self.assertIsNotNone(
            report.selected_source
        )

    def test_failover(self):
        good = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                    open_price=99,
                    high=101,
                    low=98,
                )
            ]
        )

        report = PublicProviderGroup(
            (
                adapter(TimeoutError()),
                good,
            )
        ).compare("BTC/USD")

        self.assertTrue(
            report.unhealthy_providers
        )

        self.assertIsNotNone(
            report.selected_source
        )

    def test_all_providers_unavailable(self):
        with self.assertRaises(MarketDataError):
            PublicProviderGroup(
                (
                    adapter(TimeoutError()),
                )
            ).get_candle("BTC/USD")

    def test_historical_provider_failover(self):
        good_payload = [
            row(
                NOW - timedelta(hours=4),
                100,
            ),
            row(
                NOW - timedelta(minutes=1),
                101,
            ),
        ]

        candles = PublicProviderGroup(
            (
                adapter(TimeoutError()),
                adapter(good_payload),
            )
        ).get_candles(
            "BTC/USD",
            "4H",
            limit=2,
        )

        self.assertEqual(
            2,
            len(candles),
        )

        self.assertEqual(
            101.0,
            candles[-1].close,
        )

        self.assertEqual(
            "Binance.US",
            candles[-1].provider,
        )

    def test_historical_provider_conflict_fails_closed(self):
        first = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                )
            ]
        )

        second = BinanceUSPublicAdapter(
            Transport(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        200,
                    )
                ]
            ),
            Clock(NOW),
            retries=0,
        )

        with self.assertRaises(MarketDataError):
            PublicProviderGroup(
                (
                    first,
                    second,
                )
            ).get_candles(
                "BTC/USD",
                "4H",
                limit=1,
            )

    def test_historical_provider_matching_prices_are_accepted(self):
        first = adapter(
            [
                row(
                    NOW - timedelta(minutes=1),
                    100,
                )
            ]
        )

        second = BinanceUSPublicAdapter(
            Transport(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        101,
                    )
                ]
            ),
            Clock(NOW),
            retries=0,
        )

        candles = PublicProviderGroup(
            (
                first,
                second,
            )
        ).get_candles(
            "BTC/USD",
            "4H",
            limit=1,
        )

        self.assertEqual(
            1,
            len(candles),
        )

        self.assertIn(
            candles[0].close,
            (100.0, 101.0),
        )

    def test_exchange_parsers_and_no_private_capability(self):
        coin = CoinbasePublicAdapter(
            Transport(
                [
                    [
                        int(
                            (
                                NOW - timedelta(minutes=1)
                            ).timestamp()
                        ),
                        "95",
                        "110",
                        "100",
                        "105",
                        "5",
                    ]
                ]
            ),
            Clock(NOW),
            retries=0,
        )

        coin_candle = coin.get_candle(
            "BTC/USD"
        )

        self.assertEqual(
            "Coinbase",
            coin_candle.provider,
        )

        self.assertEqual(
            100.0,
            coin_candle.open,
        )

        self.assertEqual(
            110.0,
            coin_candle.high,
        )

        self.assertEqual(
            95.0,
            coin_candle.low,
        )

        self.assertEqual(
            105.0,
            coin_candle.close,
        )

        kraken = KrakenPublicAdapter(
            Transport(
                {
                    "error": [],
                    "result": {
                        "XXBTZUSD": [
                            [
                                int(
                                    (
                                        NOW
                                        - timedelta(minutes=1)
                                    ).timestamp()
                                ),
                                "95",
                                "110",
                                "90",
                                "102",
                                "0",
                                "6",
                                1,
                            ]
                        ],
                        "last": int(
                            (
                                NOW
                                - timedelta(minutes=1)
                            ).timestamp()
                        ),
                    },
                }
            ),
            Clock(NOW),
            retries=0,
        )

        kraken_candle = kraken.get_candle(
            "BTC/USD"
        )

        self.assertEqual(
            "Kraken",
            kraken_candle.provider,
        )

        self.assertEqual(
            102.0,
            kraken_candle.close,
        )

        for value in (
            adapter(
                [
                    row(
                        NOW - timedelta(minutes=1),
                        100,
                    )
                ]
            ),
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