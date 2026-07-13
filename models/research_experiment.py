"""Immutable human-governed research experiment records."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    hypothesis: str
    metric: str
    baseline_label: str
    candidate_label: str
    controlled_change: str
    created_at: datetime
    minimum_samples: int = 5
    human_approval_required: bool = True
    paper_mode_only: bool = True


@dataclass(frozen=True)
class HumanApproval:
    approved_by: str
    approved_at: datetime
    scope: str


@dataclass(frozen=True)
class ExperimentObservation:
    sample_id: str
    baseline_value: float
    candidate_value: float
    observed_at: datetime
    paper_only: bool = True


@dataclass(frozen=True)
class ExperimentResult:
    definition: ExperimentDefinition
    status: ExperimentStatus
    approval: HumanApproval
    sample_size: int
    baseline_mean: float
    candidate_mean: float
    absolute_delta: float
    relative_delta: float | None
    conclusion: str
    risks: tuple[str, ...]
    production_change_applied: bool = False
    human_review_required: bool = True

