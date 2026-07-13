"""
===============================================================================

Hermes OS

File:
agent_report.py

Purpose:
Defines the standard report format used by Hermes agents.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass(frozen=True)
class AgentReport:
    """
    Standard evidence report submitted by every Hermes agent.
    """

    agent_name: str
    status: str
    confidence: float
    facts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendation: str = "NO_ACTION"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_valid(self) -> bool:
        """
        Validate the report before Hermes trusts it.
        """

        if not self.agent_name:
            return False

        if not 0 <= self.confidence <= 100:
            return False

        if not self.status:
            return False

        return True

    def summary(self) -> str:
        """
        Return a readable one-line summary.
        """

        return (
            f"{self.agent_name} | "
            f"Status: {self.status} | "
            f"Confidence: {self.confidence:.1f}% | "
            f"Recommendation: {self.recommendation}"
        )
