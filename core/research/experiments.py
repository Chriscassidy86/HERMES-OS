"""Deterministic experiment evaluation with explicit human governance."""

from datetime import timezone
from math import isfinite
from statistics import mean

from models.research_experiment import (
    ExperimentDefinition,
    ExperimentObservation,
    ExperimentResult,
    ExperimentStatus,
    HumanApproval,
)


class ExperimentService:
    def evaluate(
        self,
        definition: ExperimentDefinition,
        observations: tuple[ExperimentObservation, ...],
        approval: HumanApproval | None,
    ) -> ExperimentResult:
        self._validate_definition(definition)
        self._validate_approval(definition, approval)
        self._validate_observations(definition, observations, approval)
        baseline = mean(item.baseline_value for item in observations)
        candidate = mean(item.candidate_value for item in observations)
        delta = candidate - baseline
        relative = delta / abs(baseline) if baseline != 0 else None
        if abs(delta) < 1e-12:
            conclusion = "No difference was observed in the supplied paper samples."
        elif delta > 0:
            conclusion = "Candidate metric was higher in the supplied paper samples."
        else:
            conclusion = "Candidate metric was lower in the supplied paper samples."
        return ExperimentResult(
            definition,
            ExperimentStatus.COMPLETED,
            approval,
            len(observations),
            round(baseline, 6),
            round(candidate, 6),
            round(delta, 6),
            round(relative, 6) if relative is not None else None,
            conclusion,
            (
                "Paper and fixture results may not generalize.",
                "A completed experiment cannot change production configuration.",
                "A human must review any separate adoption proposal.",
            ),
        )

    @staticmethod
    def _validate_definition(definition: ExperimentDefinition) -> None:
        if not isinstance(definition, ExperimentDefinition):
            raise ValueError("An experiment definition is required.")
        text = (
            definition.experiment_id,
            definition.hypothesis,
            definition.metric,
            definition.baseline_label,
            definition.candidate_label,
            definition.controlled_change,
        )
        if any(not value.strip() for value in text):
            raise ValueError("Experiment definition fields are required.")
        if definition.baseline_label == definition.candidate_label:
            raise ValueError("Baseline and candidate labels must differ.")
        if definition.created_at.tzinfo is None:
            raise ValueError("Experiment creation timestamp must be timezone-aware.")
        if isinstance(definition.minimum_samples, bool) or definition.minimum_samples < 2:
            raise ValueError("Experiments require at least two samples.")
        if not definition.human_approval_required or not definition.paper_mode_only:
            raise ValueError("Experiments must require human approval and remain paper-only.")

    @staticmethod
    def _validate_approval(
        definition: ExperimentDefinition, approval: HumanApproval | None
    ) -> None:
        if not isinstance(approval, HumanApproval):
            raise ValueError("Explicit human approval is required before evaluation.")
        if not approval.approved_by.strip() or not approval.scope.strip():
            raise ValueError("Approval identity and scope are required.")
        if approval.scope != definition.experiment_id:
            raise ValueError("Approval scope does not match the experiment.")
        if approval.approved_at.tzinfo is None or approval.approved_at < definition.created_at:
            raise ValueError("Approval timestamp is invalid.")

    @staticmethod
    def _validate_observations(
        definition: ExperimentDefinition,
        observations: tuple[ExperimentObservation, ...],
        approval: HumanApproval,
    ) -> None:
        if len(observations) < definition.minimum_samples:
            raise ValueError("Insufficient experiment samples.")
        identifiers = set()
        for item in observations:
            if not isinstance(item, ExperimentObservation) or not item.sample_id.strip():
                raise ValueError("Experiment observations and sample identifiers are required.")
            if item.sample_id in identifiers:
                raise ValueError("Experiment sample identifiers must be unique.")
            identifiers.add(item.sample_id)
            values = (item.baseline_value, item.candidate_value)
            if any(isinstance(value, bool) or not isfinite(value) for value in values):
                raise ValueError("Experiment metrics must be finite numbers.")
            if item.observed_at.tzinfo is None or item.observed_at < approval.approved_at:
                raise ValueError("Experiment observations must follow approval.")
            if not item.paper_only:
                raise ValueError("Only paper observations are permitted.")

