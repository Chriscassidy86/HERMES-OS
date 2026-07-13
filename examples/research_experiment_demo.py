"""Evaluate one deterministic, explicitly approved paper research experiment."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.research import ExperimentService
from models.research_experiment import (
    ExperimentDefinition,
    ExperimentObservation,
    HumanApproval,
)


CREATED = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
definition = ExperimentDefinition(
    "EXP-001",
    "A bounded research threshold changes the supplied paper metric.",
    "fixture_score",
    "baseline",
    "candidate",
    "research_threshold: 0.50 -> 0.55",
    CREATED,
)
approval = HumanApproval("human-research-owner", CREATED + timedelta(minutes=1), "EXP-001")
observations = tuple(
    ExperimentObservation(f"sample-{index}", float(index), float(index) + 0.25,
                          CREATED + timedelta(minutes=2 + index))
    for index in range(5)
)
result = ExperimentService().evaluate(definition, observations, approval)
print("PAPER MODE ONLY")
print(result.conclusion)
print("Samples:", result.sample_size, "Delta:", result.absolute_delta)
print("Production change applied:", result.production_change_applied)
print("Human review required:", result.human_review_required)

