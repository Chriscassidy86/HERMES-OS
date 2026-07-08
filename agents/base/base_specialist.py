"""
===============================================================================

Hermes OS

File:
base_specialist.py

Purpose:
Base class for every Hermes specialist.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from abc import ABC, abstractmethod
from reports.agent_report import AgentReport


class BaseSpecialist(ABC):
    """
    Base class for every Hermes specialist.
    """

    def __init__(self, name: str):
        self.name = name

    def create_report(
        self,
        status: str,
        confidence: float,
        facts: list[str],
        warnings: list[str],
        recommendation: str,
    ) -> AgentReport:
        """
        Create a standard AgentReport.
        """

        return AgentReport(
            agent_name=self.name,
            status=status,
            confidence=confidence,
            facts=facts,
            warnings=warnings,
            recommendation=recommendation,
        )

    @abstractmethod
    def analyze(self, snapshot):
        """
        Every specialist must analyze a MarketSnapshot.
        """
        pass