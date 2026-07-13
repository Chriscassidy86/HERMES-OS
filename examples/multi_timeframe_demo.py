"""Aggregate one supplied specialist across five deterministic timeframes."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.recommendation.recommendation_engine import RecommendationEngine
from core.timeframes import MultiTimeframeEngine
from models.signal import Signal


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
signals = tuple(Signal("Trend Specialist", "LONG", 80, 0.8, timeframe, 2, NOW,
                       (f"{timeframe} supplied trend is bullish.",))
                for timeframe in ("5m", "15m", "1h", "4h", "Daily"))
summary = MultiTimeframeEngine().analyze("BTC/USD", signals, as_of=NOW)
recommendation = RecommendationEngine().recommend_multi_timeframe(summary)
print("PAPER MODE ONLY - MULTI-TIMEFRAME RESEARCH")
for item in summary.specialists:
    print(item.source, item.short_term.direction, item.medium_term.direction, item.long_term.direction)
print(recommendation.summary())

