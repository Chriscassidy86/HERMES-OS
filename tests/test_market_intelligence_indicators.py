import unittest

from agents.market_intelligence.indicators import (
    atr,
    bollinger_bands,
    detect_swings,
    ema,
    macd,
    obv,
    obv_series,
    relative_volume,
    rsi,
    sma,
    stochastic,
    volume_spikes,
)


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        self.closes = list(range(100, 151))

        self.highs = [
            price + 2
            for price in self.closes
        ]

        self.lows = [
            price - 2
            for price in self.closes
        ]

        self.volumes = [
            100 + (index * 5)
            for index in range(len(self.closes))
        ]

    def test_sma(self):
        self.assertEqual(
            sma([1, 2, 3, 4, 5], 3),
            4.0,
        )
        self.assertIsNone(
            sma([1, 2], 3)
        )

    def test_ema(self):
        self.assertEqual(
            ema([1, 2, 3, 4, 5], 3),
            4.0,
        )
        self.assertIsNone(
            ema([1, 2], 3)
        )

    def test_rsi(self):
        value = rsi(
            self.closes,
            14,
        )

        self.assertIsNotNone(value)
        self.assertGreaterEqual(
            value,
            0.0,
        )
        self.assertLessEqual(
            value,
            100.0,
        )

    def test_macd(self):
        result = macd(
            self.closes,
        )

        self.assertIsNotNone(result)

        macd_line, signal_line, histogram = result

        self.assertIsInstance(
            macd_line,
            float,
        )
        self.assertIsInstance(
            signal_line,
            float,
        )
        self.assertIsInstance(
            histogram,
            float,
        )

    def test_stochastic(self):
        result = stochastic(
            self.highs,
            self.lows,
            self.closes,
        )

        self.assertIsNotNone(result)

        percent_k, percent_d = result

        self.assertGreaterEqual(
            percent_k,
            0.0,
        )
        self.assertLessEqual(
            percent_k,
            100.0,
        )
        self.assertGreaterEqual(
            percent_d,
            0.0,
        )
        self.assertLessEqual(
            percent_d,
            100.0,
        )

    def test_atr(self):
        value = atr(
            self.highs,
            self.lows,
            self.closes,
            14,
        )

        self.assertIsNotNone(value)
        self.assertGreater(
            value,
            0.0,
        )

    def test_bollinger_bands(self):
        result = bollinger_bands(
            self.closes,
            20,
        )

        self.assertIsNotNone(result)

        middle, upper, lower = result

        self.assertGreater(
            upper,
            middle,
        )
        self.assertLess(
            lower,
            middle,
        )

    def test_relative_volume(self):
        value = relative_volume(
            self.volumes,
            20,
        )

        self.assertIsNotNone(value)
        self.assertGreater(
            value,
            0.0,
        )

    def test_volume_spikes(self):
        volumes = self.volumes[:40]

        # Make the final 20 candles contain several obvious spikes.
        volumes[-5:] = [
            1000,
            1100,
            1200,
            1300,
            1400,
        ]

        result = volume_spikes(
            volumes,
            20,
            2.0,
        )

        self.assertIsNotNone(result)
        self.assertGreater(
            result,
            0,
        )

    def test_obv(self):
        value = obv(
            self.closes,
            self.volumes,
        )

        self.assertIsNotNone(value)

        series = obv_series(
            self.closes,
            self.volumes,
        )

        self.assertEqual(
            len(series),
            len(self.closes),
        )
        self.assertEqual(
            series[-1],
            value,
        )

    def test_detect_swings(self):
        # Use a deliberately oscillating series so local highs/lows exist.
        closes = [
            100, 105, 102, 108, 104,
            110, 106, 112, 108, 114,
            110, 116, 112, 118, 114,
            120, 116, 122, 118, 124,
        ]

        result = detect_swings(
            closes,
            20,
        )

        self.assertIsNotNone(result)

        higher_highs, lower_lows = result

        self.assertIsInstance(
            higher_highs,
            bool,
        )
        self.assertIsInstance(
            lower_lows,
            bool,
        )

    def test_insufficient_data_returns_none(self):
        self.assertIsNone(
            rsi([1, 2, 3], 14)
        )

        self.assertIsNone(
            macd([1, 2, 3])
        )

        self.assertIsNone(
            stochastic(
                [3, 3],
                [1, 1],
                [2, 2],
                14,
                3,
            )
        )

        self.assertIsNone(
            atr(
                [3, 3],
                [1, 1],
                [2, 2],
                14,
            )
        )

        self.assertIsNone(
            bollinger_bands(
                [1, 2],
                20,
            )
        )

        self.assertIsNone(
            relative_volume(
                [100, 110],
                20,
            )
        )

        self.assertIsNone(
            volume_spikes(
                [100, 110],
                20,
            )
        )


if __name__ == "__main__":
    unittest.main()