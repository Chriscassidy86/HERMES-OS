"""Immutable executive and research briefing records."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from models.specialist_intelligence import SpecialistAssessment
from models.decision_explanation import DecisionExplanation


class BriefingPeriod(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


@dataclass(frozen=True)
class BriefingFacts:
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    system_health: str
    decision_cycles: int
    paper_eligible_cycles: int
    rejected_cycles: int
    realized_paper_pnl: float
    maximum_paper_drawdown: float
    specialist_assessments: tuple[SpecialistAssessment, ...] = ()
    research_notes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    decision_explanations: tuple[DecisionExplanation, ...] = ()


@dataclass(frozen=True)
class ResearchBriefing:
    period: BriefingPeriod
    title: str
    generated_at: datetime
    executive_summary: tuple[str, ...]
    research_observations: tuple[str, ...]
    risks: tuple[str, ...]
    limitations: tuple[str, ...]
    paper_mode_only: bool = True

    def render(self) -> str:
        sections = (
            ("EXECUTIVE SUMMARY", self.executive_summary),
            ("RESEARCH OBSERVATIONS", self.research_observations),
            ("RISKS", self.risks),
            ("LIMITATIONS", self.limitations),
        )
        lines = [self.title, f"Generated: {self.generated_at.isoformat()}", "Mode: PAPER ONLY"]
        for heading, values in sections:
            lines.extend(("", heading))
            lines.extend(f"- {value}" for value in values)
        return "\n".join(lines) + "\n"

