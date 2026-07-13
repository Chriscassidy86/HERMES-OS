"""Render one labeled PAPER performance report."""
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from models.performance_analytics import PerformanceObservation
from services.performance_analytics import PerformanceAnalyticsService
item = PerformanceObservation("1", datetime(2026, 7, 13, tzinfo=timezone.utc), "PAPER", "BTC/USD", "BULL", "5m", "trend", 2, 0, 102, .2, 1, .1, .05, .7, True, "WIN")
service = PerformanceAnalyticsService(); print(service.serialize(service.analyze((item,), starting_equity=100)))
