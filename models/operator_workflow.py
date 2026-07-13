"""Immutable local alerts and daily operator workflow records."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OperatorAlert:
    alert_id: str
    category: str
    severity: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    local_only: bool = True


@dataclass(frozen=True)
class WorkflowStep:
    number: int
    label: str
    completed: bool = False
    completed_at: datetime | None = None


@dataclass(frozen=True)
class DailyWorkflowReport:
    mode: str
    steps: tuple[WorkflowStep, ...]
    complete: bool
    missing_steps: tuple[str, ...]
    live_actions_available: bool = False
