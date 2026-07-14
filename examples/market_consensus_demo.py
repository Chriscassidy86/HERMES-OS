"""Deterministic advisory market-consensus domain example."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from models.market_consensus import ConsensusDirection, ConsensusObservation, ConsensusSignal, ConsensusSnapshot, ConsensusSource, SourceCategory, stable_json


now = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
source = ConsensusSource("hermes-public-price", "Hermes Public Price Evidence", SourceCategory.PUBLIC_EXCHANGE_METRICS, 0.8, "VERIFIED_PUBLIC", "PUBLIC", "Validated unauthenticated public snapshot", True)
signal = ConsensusSignal(ConsensusDirection.LEAN_BULLISH, 0.3, 0.7, 0.4, ("One source is not independent consensus.",))
observation = ConsensusObservation.create(observation_id="DEMO-1", source=source, symbol="BTC/USD", timeframe="1H", observed_at=now, ingested_at=now, raw_value=100.0, signal=signal)
snapshot = ConsensusSnapshot.build("BTC/USD", "1H", now, (observation,))
print(stable_json(snapshot))
print("ADVISORY ONLY: outside evidence cannot cause execution or bypass Risk Manager.")
