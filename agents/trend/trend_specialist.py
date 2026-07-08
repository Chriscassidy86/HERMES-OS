"""
===============================================================================

Hermes OS

File:
trend_specialist.py

Purpose:
Trend specialist for analyzing market direction.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from agents.base.base_specialist import BaseSpecialist


class TrendSpecialist(BaseSpecialist):
    """
    Analyzes the market trend from a MarketSnapshot.
    """

    def __init__(self):
        super().__init__("Trend Specialist")

    def analyze(self, snapshot):
        """
        Analyze market trend and return an AgentReport.
        """

        if snapshot.market_trend.lower() == "bullish":
            return self.create_report(
                status="BULLISH",
                confidence=80.0,
                facts=[
                    f"{snapshot.symbol} market trend is bullish",
                    f"Current price is ${snapshot.price:,.2f}",
                ],
                warnings=[],
                recommendation="TREND_FOLLOWING_ALLOWED",
            )

        return self.create_report(
            status="NEUTRAL",
            confidence=50.0,
            facts=[
                f"{snapshot.symbol} market trend is {snapshot.market_trend}",
            ],
            warnings=[
                "Trend is not clearly bullish",
            ],
            recommendation="WAIT_FOR_CONFIRMATION",
        )