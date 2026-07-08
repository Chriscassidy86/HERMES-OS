"""
===============================================================================

Hermes OS

File:
evidence_summary.py

Purpose:
Represents the summarized evidence gathered from all specialist signals.

Created By:
EvidenceAnalyzer

Consumed By:
Executive Brief
Decision Engine

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceSummary:
    """
    Represents the combined evidence from Hermes specialists.
    """

    symbol: str

    bullish: int
    bearish: int
    neutral: int

    average_confidence: float

    signal_count: int

    def summary(self) -> str:
        return (
            f"{self.symbol} | "
            f"Bullish: {self.bullish} | "
            f"Bearish: {self.bearish} | "
            f"Neutral: {self.neutral} | "
            f"Average Confidence: {self.average_confidence:.2f}%"
        )