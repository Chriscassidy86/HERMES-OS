"""
===============================================================================

Hermes OS

File:
recommendation_engine.py

Purpose:
Creates a recommendation from an EvidenceSummary.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from models.evidence_summary import EvidenceSummary
from models.recommendation import Recommendation


class RecommendationEngine:
    """
    Converts summarized evidence into a Recommendation.
    """

    def recommend(self, summary: EvidenceSummary) -> Recommendation:
        if summary.directional_score >= 0.25 and summary.final_confidence >= 70:
            return Recommendation(
                symbol=summary.symbol,
                action="LONG",
                confidence=summary.average_confidence,
                reason="Bullish evidence exceeds bearish evidence with acceptable confidence.",
            )

        if summary.directional_score <= -0.25 and summary.final_confidence >= 70:
            return Recommendation(
                symbol=summary.symbol,
                action="SHORT",
                confidence=summary.average_confidence,
                reason="Bearish evidence exceeds bullish evidence with acceptable confidence.",
            )

        return Recommendation(
            symbol=summary.symbol,
            action="WAIT",
            confidence=summary.average_confidence,
            reason="Evidence is not strong enough for a directional recommendation.",
        )
