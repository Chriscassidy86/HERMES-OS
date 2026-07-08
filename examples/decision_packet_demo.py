from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.signal import Signal
from models.decision_packet import DecisionPacket


packet = DecisionPacket(symbol="BTC/USD")

trend_signal = Signal(
    source="Trend Specialist",
    direction="LONG",
    confidence=80.0,
    strength=0.78,
    timeframe="4H",
    priority=2,
)

volume_signal = Signal(
    source="Volume Specialist",
    direction="WAIT",
    confidence=61.0,
    strength=0.52,
    timeframe="4H",
    priority=3,
)

packet = packet.add_signal(trend_signal)
packet = packet.add_signal(volume_signal)

print(packet.summary())

print("\nSignals Received:")

for signal in packet.signals:
    print("-", signal.summary())