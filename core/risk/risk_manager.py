"""
===============================================================================

Hermes OS

File:
risk_manager.py

Purpose:
Evaluates recommendations and produces a RiskAssessment.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from math import isfinite

from models.recommendation import Recommendation
from models.risk_assessment import RiskAssessment


class RiskManager:
    """
    Performs Hermes' first layer of risk evaluation.
    """

    def evaluate(self, recommendation: Recommendation) -> RiskAssessment:

        if (
            recommendation.action not in {"LONG", "SHORT"}
            or not isinstance(recommendation.confidence, (int, float))
            or isinstance(recommendation.confidence, bool)
            or not isfinite(recommendation.confidence)
            or not 0 <= recommendation.confidence <= 100
        ):
            return RiskAssessment(
                symbol=recommendation.symbol,
                approved=False,
                risk_score=100,
                max_position_size=0.0,
                max_loss=0.0,
                reason="Recommendation is not a valid directional trade.",
            )

        if recommendation.confidence >= 80:
            return RiskAssessment(
                symbol=recommendation.symbol,
                approved=True,
                risk_score=20,
                max_position_size=25.00,
                max_loss=1.25,
                reason="High confidence recommendation.",
            )

        if recommendation.confidence >= 70:
            return RiskAssessment(
                symbol=recommendation.symbol,
                approved=True,
                risk_score=35,
                max_position_size=20.00,
                max_loss=1.00,
                reason="Acceptable confidence. Trade allowed with reduced size.",
            )

        return RiskAssessment(
            symbol=recommendation.symbol,
            approved=False,
            risk_score=75,
            max_position_size=0.0,
            max_loss=0.0,
            reason="Confidence below minimum threshold.",
        )
