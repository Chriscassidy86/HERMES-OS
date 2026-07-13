"""Immutable human-readable explanation of one Hermes decision."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DecisionExplanation:
    cycle_id: str
    recommendation: str
    confidence: float
    what_is_happening: str
    why: tuple[str, ...]
    agreeing_specialists: tuple[str, ...]
    disagreeing_specialists: tuple[str, ...]
    ignored_evidence: tuple[str, ...]
    ignored_reasons: tuple[str, ...]
    risk_explanation: str
    assumptions: tuple[str, ...]
    uncertainties: tuple[str, ...]
    generated_at: datetime

    def executive_summary(self) -> str:
        return (
            f"{self.what_is_happening} Recommendation: {self.recommendation} "
            f"at {self.confidence:.2f}% confidence. {self.risk_explanation}"
        )

