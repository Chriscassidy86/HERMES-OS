"""
===============================================================================

Hermes OS

File:
risk_assessment.py

Purpose:
Represents the Risk Department's evaluation of a recommendation.

Created By:
Risk Department

Consumed By:
Portfolio Department

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    """
    Represents the risk evaluation performed before a trade.
    """

    symbol: str

    approved: bool

    risk_score: int

    max_position_size: float

    max_loss: float

    reason: str

    def summary(self) -> str:
        return (
            f"{self.symbol} | "
            f"Approved: {self.approved} | "
            f"Risk Score: {self.risk_score} | "
            f"Max Position: ${self.max_position_size:.2f} | "
            f"Max Loss: ${self.max_loss:.2f}"
        )