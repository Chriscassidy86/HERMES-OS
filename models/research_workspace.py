"""Immutable records for bounded, local research jobs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchJobDefinition:
    job_id: str
    run_id: str
    kind: str
    dataset_ids: tuple[str, ...]
    configuration_labels: tuple[str, ...]
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    resource_limit: int
    human_approval_state: str
    mode: str = "PAPER"


@dataclass(frozen=True)
class ResearchJobStatus:
    job_id: str
    state: str
    progress: int
    warning: str | None = None
    result_run_id: str | None = None
    configuration_modified: bool = False
