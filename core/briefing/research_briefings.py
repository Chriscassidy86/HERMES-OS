"""Deterministic daily, weekly, and monthly research briefing service."""

from datetime import timezone
from math import isfinite

from models.research_briefing import BriefingFacts, BriefingPeriod, ResearchBriefing


class ResearchBriefingService:
    def daily(self, facts: BriefingFacts) -> ResearchBriefing:
        return self._build(BriefingPeriod.DAILY, facts)

    def weekly(self, facts: BriefingFacts) -> ResearchBriefing:
        return self._build(BriefingPeriod.WEEKLY, facts)

    def monthly(self, facts: BriefingFacts) -> ResearchBriefing:
        return self._build(BriefingPeriod.MONTHLY, facts)

    def _build(self, period: BriefingPeriod, facts: BriefingFacts) -> ResearchBriefing:
        self._validate(facts)
        start = facts.period_start.astimezone(timezone.utc)
        end = facts.period_end.astimezone(timezone.utc)
        generated = facts.generated_at.astimezone(timezone.utc)
        observations = list(facts.research_notes)
        for explanation in facts.decision_explanations:
            observations.append(explanation.executive_summary())
            observations.extend(f"Uncertainty: {item}" for item in explanation.uncertainties)
        for assessment in sorted(facts.specialist_assessments, key=lambda item: item.source):
            observations.append(
                f"{assessment.source}: {assessment.status}; score={assessment.score:.4f}; advisory only."
            )
        if not observations:
            observations.append("No validated research observations were supplied for this period.")
        risks = [
            f"Rejected or invalid cycles: {facts.rejected_cycles}.",
            f"Maximum observed paper drawdown: {facts.maximum_paper_drawdown:.2f}.",
        ]
        for assessment in facts.specialist_assessments:
            risks.extend(assessment.warnings)
        limitations = list(facts.limitations)
        limitations.append(
            "Paper, fixture, replay, and limited observations are not evidence of real profitability."
        )
        return ResearchBriefing(
            period,
            f"HERMES {period.value} EXECUTIVE RESEARCH BRIEF | {start.date()} to {end.date()}",
            generated,
            (
                f"System health: {facts.system_health}.",
                f"Decision cycles: {facts.decision_cycles}; paper eligible: {facts.paper_eligible_cycles}.",
                f"Realized paper P&L: {facts.realized_paper_pnl:.2f}.",
            ),
            tuple(observations),
            tuple(dict.fromkeys(risks)),
            tuple(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _validate(facts: BriefingFacts) -> None:
        if not isinstance(facts, BriefingFacts):
            raise ValueError("Briefing facts are required.")
        times = (facts.period_start, facts.period_end, facts.generated_at)
        if any(value.tzinfo is None for value in times):
            raise ValueError("Briefing timestamps must be timezone-aware.")
        if facts.period_end < facts.period_start or facts.generated_at < facts.period_end:
            raise ValueError("Briefing time range is invalid or incomplete.")
        counts = (facts.decision_cycles, facts.paper_eligible_cycles, facts.rejected_cycles)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("Briefing counts must be non-negative integers.")
        if facts.paper_eligible_cycles > facts.decision_cycles or facts.rejected_cycles > facts.decision_cycles:
            raise ValueError("Briefing counts are contradictory.")
        metrics = (facts.realized_paper_pnl, facts.maximum_paper_drawdown)
        if any(isinstance(value, bool) or not isfinite(value) for value in metrics):
            raise ValueError("Briefing performance metrics must be finite.")
        if facts.maximum_paper_drawdown < 0:
            raise ValueError("Maximum paper drawdown cannot be negative.")
        if not facts.system_health.strip():
            raise ValueError("System health is required.")
        if any(not item.advisory_only for item in facts.specialist_assessments):
            raise ValueError("Only advisory specialist assessments may enter research briefings.")
        if any(item.generated_at > facts.generated_at for item in facts.decision_explanations):
            raise ValueError("Future decision explanations cannot enter a briefing.")

