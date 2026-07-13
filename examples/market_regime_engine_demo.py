"""Classify one deterministic supplied market-regime fixture."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.regime import MarketRegimeEngine
from models.market_regime import RegimeInputs


inputs = RegimeInputs("BTC/USD", 111, 108, 106, 102, 1500, 1000, 2, 2,
                      110, 90, 0.62, datetime(2026, 7, 13, 12, tzinfo=timezone.utc))
result = MarketRegimeEngine().classify(inputs)
print("PAPER MODE ONLY - RESEARCH CLASSIFICATION")
print(result.regime.value, result.confidence)
print(result.explanation)
print("Uncertainty:", "; ".join(result.uncertainty))

