from datetime import datetime,timezone
from pathlib import Path
import tempfile,unittest

from backtests.historical_import import HistoricalCsvCandleLoader
from backtests.replay import FixtureCandleLoader,ReplayConfig,ReplaySession

CSV_BODY="""symbol,timestamp,open,high,low,close,volume,timeframe
ETH/USD,2026-07-11T04:00:00Z,90,95,88,92,800,15m
BTC/USD,2026-07-11T04:00:00Z,100,107,99,105,1500,15m
BTC/USD,2026-07-11T00:00:00Z,98,102,97,100,1000,15m
BTC/USD,2026-07-11T08:00:00Z,105,112,104,110,1800,15m
"""

class HistoricalImportTests(unittest.TestCase):
    def write_csv(self,body=CSV_BODY):
        tempdir=tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        path=Path(tempdir.name)/"history.csv"
        path.write_text(body,encoding="utf-8")
        return path
    def test_csv_loader_filters_sorts_and_derives_candles(self):
        candles=HistoricalCsvCandleLoader(self.write_csv(),symbol="BTC/USD",timeframe="15m",short_window=2,long_window=3,volume_window=2).load()
        self.assertEqual(3,len(candles))
        self.assertEqual("BTC/USD",candles[0].symbol)
        self.assertEqual(datetime(2026,7,11,0,0,tzinfo=timezone.utc),candles[0].timestamp)
        self.assertEqual(98,candles[0].previous_close)
        self.assertEqual("Bullish",candles[0].trend)
        self.assertAlmostEqual(100.0,candles[0].short_ma)
        self.assertAlmostEqual(100.0,candles[0].long_ma)
        self.assertAlmostEqual(1000.0,candles[0].average_volume)
        self.assertAlmostEqual(5.0,candles[0].volatility)
        self.assertEqual("15m",candles[0].timeframe)
        self.assertLess(candles[0].timestamp,candles[1].timestamp)
    def test_csv_loader_requires_symbol_filter_for_mixed_files(self):
        with self.assertRaises(ValueError): HistoricalCsvCandleLoader(self.write_csv()).load()
    def test_imported_candles_can_run_through_replay(self):
        candles=HistoricalCsvCandleLoader(self.write_csv(),symbol="BTC/USD",timeframe="15m").load()
        result=ReplaySession(FixtureCandleLoader(candles),ReplayConfig()).run()
        self.assertEqual(2,len(result.decisions))
        self.assertEqual(3,len(result.equity_history))
        self.assertIsNotNone(result.metrics)

if __name__=="__main__": unittest.main()
