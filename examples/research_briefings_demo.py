"""Render deterministic sample briefings from supplied paper-only facts."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.briefing import ResearchBriefingService
from models.research_briefing import BriefingFacts


END = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def facts(days: int) -> BriefingFacts:
    return BriefingFacts(
        period_start=END - timedelta(days=days),
        period_end=END,
        generated_at=END,
        system_health="HEALTHY",
        decision_cycles=12,
        paper_eligible_cycles=4,
        rejected_cycles=2,
        realized_paper_pnl=18.25,
        maximum_paper_drawdown=7.5,
        research_notes=("Supplied fixture evidence remained internally consistent.",),
        limitations=("Sample size is limited.",),
    )


if __name__ == "__main__":
    service = ResearchBriefingService()
    for briefing in (service.daily(facts(1)), service.weekly(facts(7)), service.monthly(facts(30))):
        print(briefing.render())
