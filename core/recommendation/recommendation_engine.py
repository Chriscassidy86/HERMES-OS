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


class RecommendationEngine:
    """
    Converts summarized evidence into a recommendation.
    """

    def recommend(self, summary: EvidenceSummary) -> str:
        if summary.bullish > summary.bearish and summary.average_confidence >= 70:
            return "RECOMMEND_LONG"

        if summary.bearish > summary.bullish and summary.average_confidence >= 70:
            return "RECOMMEND_SHORT"

        return "RECOMMEND_WAIT"