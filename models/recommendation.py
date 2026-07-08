"""
===============================================================================

Hermes OS

File:
recommendation.py

Purpose:
Represents the recommendation produced by the Recommendation Engine.

Created By:
RecommendationEngine

Consumed By:
Risk Department

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """
    Represents Hermes' recommendation before risk review.
    """

    symbol: str

    action: str

    confidence: float

    reason: str

    requires_risk_review: bool = True

    def summary(self) -> str:
        return (
            f"{self.symbol} | "
            f"{self.action} | "
            f"Confidence: {self.confidence:.2f}% | "
            f"Risk Review Required: {self.requires_risk_review}"
        )