from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from core.briefing import ResearchBriefingService
from models.research_briefing import BriefingFacts, BriefingPeriod
from models.specialist_intelligence import SpecialistAssessment


END = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def facts(**changes):
    value = BriefingFacts(
        END - timedelta(days=1), END, END, "HEALTHY", 10, 4, 2, 12.5, 3.0,
        (SpecialistAssessment("Liquidity Specialist", "BTC/USD", "HEALTHY", 0.9, 90.0,
                              ("spread",), (), END),),
        ("One deterministic observation.",), ("Small sample.",),
    )
    return replace(value, **changes)


class ResearchBriefingTests(unittest.TestCase):
    def test_daily_weekly_and_monthly_are_deterministic(self):
        service = ResearchBriefingService()
        values = (service.daily(facts()), service.weekly(facts()), service.monthly(facts()))
        self.assertEqual((BriefingPeriod.DAILY, BriefingPeriod.WEEKLY, BriefingPeriod.MONTHLY),
                         tuple(value.period for value in values))
        self.assertEqual(values[0], service.daily(facts()))

    def test_render_separates_executive_research_risk_and_limitations(self):
        text = ResearchBriefingService().daily(facts()).render()
        for heading in ("EXECUTIVE SUMMARY", "RESEARCH OBSERVATIONS", "RISKS", "LIMITATIONS"):
            self.assertIn(heading, text)
        self.assertIn("not evidence of real profitability", text)
        self.assertIn("PAPER ONLY", text)

    def test_assessment_is_advisory_and_sorted(self):
        first = SpecialistAssessment("Z Specialist", "BTC/USD", "OK", 0.5, 50.0, ("z",), (), END)
        second = SpecialistAssessment("A Specialist", "BTC/USD", "OK", 0.5, 50.0, ("a",), (), END)
        result = ResearchBriefingService().daily(facts(specialist_assessments=(first, second)))
        self.assertTrue(result.research_observations[1].startswith("A Specialist"))

    def test_invalid_or_future_incomplete_period_fails_closed(self):
        with self.assertRaises(ValueError):
            ResearchBriefingService().daily(facts(generated_at=END - timedelta(seconds=1)))
        with self.assertRaises(ValueError):
            ResearchBriefingService().daily(facts(decision_cycles=1, rejected_cycles=2))

    def test_non_advisory_assessment_is_rejected(self):
        assessment = replace(facts().specialist_assessments[0], advisory_only=False)
        with self.assertRaises(ValueError):
            ResearchBriefingService().daily(facts(specialist_assessments=(assessment,)))

    def test_briefing_is_immutable(self):
        result = ResearchBriefingService().daily(facts())
        with self.assertRaises(FrozenInstanceError):
            result.title = "changed"


if __name__ == "__main__":
    unittest.main()
