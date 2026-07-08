from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.signal import Signal
from models.decision_packet import DecisionPacket
from core.evidence.evidence_analyzer import EvidenceAnalyzer


packet = DecisionPacket(symbol="BTC/USD")

packet = packet.add_signal(
    Signal(
        source="Trend Specialist",
        direction="LONG",
        confidence=80.0,
        strength=0.78,
        timeframe="4H",
        priority=2,
    )
)

packet = packet.add_signal(
    Signal(
        source="Volume Specialist",
        direction="WAIT",
        confidence=61.0,
        strength=0.52,
        timeframe="4H",
        priority=3,
    )
)

packet = packet.add_signal(
    Signal(
        source="News Specialist",
        direction="LONG",
        confidence=74.0,
        strength=0.69,
        timeframe="4H",
        priority=2,
    )
)

analyzer = EvidenceAnalyzer()

summary = analyzer.analyze(packet)

print("====================================================")
print("        HERMES EVIDENCE SUMMARY")
print("====================================================")

for key, value in summary.items():
    print(f"{key}: {value}")