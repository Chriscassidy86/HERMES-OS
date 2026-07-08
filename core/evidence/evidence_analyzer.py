"""
===============================================================================

Hermes OS

File:
evidence_analyzer.py

Purpose:
Summarizes specialist signals before the Decision Engine evaluates them.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from models.decision_packet import DecisionPacket


class EvidenceAnalyzer:
    """
    Analyzes the evidence collected from Hermes specialists.
    """

    def analyze(self, packet: DecisionPacket) -> dict:

        bullish = 0
        bearish = 0
        neutral = 0

        total_confidence = 0.0

        for signal in packet.signals:

            total_confidence += signal.confidence

            if signal.direction == "LONG":
                bullish += 1

            elif signal.direction == "SHORT":
                bearish += 1

            else:
                neutral += 1

        average_confidence = (
            total_confidence / len(packet.signals)
            if packet.signals
            else 0
        )

        return {
            "symbol": packet.symbol,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "average_confidence": round(average_confidence, 2),
            "signal_count": packet.signal_count(),
        }