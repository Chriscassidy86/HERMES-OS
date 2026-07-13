from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.signal import Signal


signal = Signal(
    source="Trend Specialist",
    direction="LONG",
    confidence=80.0,
    strength=0.78,
    timeframe="4H",
    priority=2,
)

print(signal.summary())
