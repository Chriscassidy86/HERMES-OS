"""Bounded local replay and research job state machine."""

from core.research.provenance import stable_checksum
from models.research_workspace import ResearchJobDefinition, ResearchJobStatus
from services.research_reproducibility import (
    ReproducibilityExporter,
    ResearchComparisonService,
)


RESEARCH_JOB_KINDS = {
    "REPLAY",
    "WALK_FORWARD",
    "EXPERIMENT",
    "MULTI_SYMBOL",
    "MULTI_TIMEFRAME",
}


class ResearchWorkspace:
    """Runs deterministic PAPER research without an adoption or trading path."""

    def __init__(self, orchestrator, repository, *, max_jobs=20):
        if isinstance(max_jobs, bool) or not isinstance(max_jobs, int) or max_jobs < 1:
            raise ValueError("Workspace capacity must be a positive integer.")
        self.orchestrator = orchestrator
        self.repository = repository
        self.max_jobs = max_jobs
        self.definitions = {}
        self.statuses = {}
        self.inputs = {}

    def define(
        self,
        *,
        run_id,
        kind,
        dataset_rows,
        configurations,
        symbols,
        timeframes,
        resource_limit=10_000,
        human_approval_state="HUMAN_REVIEW",
    ):
        configurations = tuple(configurations)
        symbols = tuple(symbols)
        timeframes = tuple(timeframes)
        if (
            kind not in RESEARCH_JOB_KINDS
            or not str(run_id).strip()
            or not dataset_rows
            or not configurations
            or not symbols
            or not timeframes
        ):
            raise ValueError("Research job definition is invalid.")
        if (
            isinstance(resource_limit, bool)
            or not isinstance(resource_limit, int)
            or resource_limit < 1
            or len(dataset_rows) > 20
            or len(configurations) > 10
        ):
            raise ValueError("Research job exceeds bounded resources.")
        materialized_rows = {
            str(dataset_id): tuple(rows)
            for dataset_id, rows in dataset_rows.items()
        }
        if sum(len(rows) for rows in materialized_rows.values()) > resource_limit:
            raise ValueError("Research job exceeds bounded resources.")
        seed = (
            run_id,
            kind,
            tuple((key, stable_checksum(value)) for key, value in sorted(materialized_rows.items())),
            tuple((configuration.label, configuration.fingerprint, configuration.signal_threshold) for configuration in configurations),
            tuple(sorted(str(symbol) for symbol in symbols)),
            tuple(sorted(str(timeframe) for timeframe in timeframes)),
        )
        job_id = "JOB-" + stable_checksum(seed)[:16]
        definition = ResearchJobDefinition(
            job_id=job_id,
            run_id=str(run_id),
            kind=kind,
            dataset_ids=tuple(sorted(materialized_rows)),
            configuration_labels=tuple(
                configuration.label for configuration in configurations
            ),
            symbols=tuple(sorted(str(symbol) for symbol in symbols)),
            timeframes=tuple(sorted(str(timeframe) for timeframe in timeframes)),
            resource_limit=resource_limit,
            human_approval_state=str(human_approval_state),
        )
        return definition, materialized_rows, configurations

    def submit(self, definition, dataset_rows, configurations):
        if not isinstance(definition, ResearchJobDefinition):
            raise ValueError("An immutable research job definition is required.")
        if definition.mode != "PAPER":
            raise ValueError("Research workspace is PAPER-only.")
        dataset_rows = {str(key): tuple(value) for key, value in dataset_rows.items()}
        configurations = tuple(configurations)
        if (
            tuple(sorted(dataset_rows)) != definition.dataset_ids
            or tuple(item.label for item in configurations) != definition.configuration_labels
            or sum(len(value) for value in dataset_rows.values()) > definition.resource_limit
        ):
            raise ValueError("Submitted research inputs do not match the bounded definition.")
        if len(self.definitions) >= self.max_jobs:
            raise ValueError("Workspace job capacity reached.")
        if (
            definition.job_id in self.definitions
            or self.repository.load_run(definition.run_id) is not None
        ):
            raise ValueError("Duplicate research job or run.")
        self.definitions[definition.job_id] = definition
        self.inputs[definition.job_id] = (dataset_rows, configurations)
        status = ResearchJobStatus(definition.job_id, "QUEUED", 0)
        self.statuses[definition.job_id] = status
        return status

    def cancel(self, job_id):
        status = self._status(job_id)
        if status.state != "QUEUED":
            raise ValueError("Only queued jobs may be cancelled safely.")
        cancelled = ResearchJobStatus(
            job_id,
            "CANCELLED",
            status.progress,
            "Cancelled safely before result publication.",
        )
        self.statuses[job_id] = cancelled
        return cancelled

    def run(self, job_id, *, code_commit="local", seed=0):
        status = self._status(job_id)
        if status.state == "CANCELLED":
            return status
        if status.state != "QUEUED":
            raise ValueError("Only queued research jobs may run.")
        self.statuses[job_id] = ResearchJobStatus(job_id, "RUNNING", 10)
        definition = self.definitions[job_id]
        dataset_rows, configurations = self.inputs[job_id]
        try:
            result = self.orchestrator.run(
                run_id=definition.run_id,
                code_commit=code_commit,
                dataset_rows=dataset_rows,
                configurations=configurations,
                reproducibility_seed=seed,
                strategy_versions=(("workspace", "1"),),
                specialist_versions=(("hermes", "1"),),
                human_approval_state=definition.human_approval_state,
            )
        except Exception as exc:
            failed = ResearchJobStatus(
                job_id,
                "FAILED",
                100,
                f"{type(exc).__name__}: {exc}",
            )
            self.statuses[job_id] = failed
            return failed
        completed = ResearchJobStatus(
            job_id,
            "COMPLETED",
            100,
            result_run_id=result.manifest.run_id,
        )
        self.statuses[job_id] = completed
        return completed

    def result(self, job_id):
        status = self._status(job_id)
        if status.result_run_id is None:
            return None
        return self.repository.load_run(status.result_run_id)

    @staticmethod
    def compare(baseline, candidate):
        return ResearchComparisonService().compare(baseline, candidate)

    @staticmethod
    def export(manifest, dependencies=()):
        return ReproducibilityExporter().export(manifest, dependencies)

    def _status(self, job_id):
        if job_id not in self.statuses:
            raise KeyError(f"Unknown research job: {job_id}")
        return self.statuses[job_id]
