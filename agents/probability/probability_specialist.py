"""Bounded evidence probability estimate for research use only."""

from datetime import timezone
from math import isfinite

from models.specialist_intelligence import ProbabilityInputs, SpecialistAssessment


class ProbabilitySpecialist:
    name = "Probability Specialist"

    def analyze(self, inputs: ProbabilityInputs) -> SpecialistAssessment:
        self._validate(inputs)
        directional = inputs.supporting_signals + inputs.opposing_signals
        agreement = inputs.supporting_signals / directional if directional else 0.5
        confidence_factor = inputs.mean_confidence / 100.0
        probability = 0.5 + (agreement - 0.5) * confidence_factor
        status = "SUPPORTING" if probability >= 0.6 else ("OPPOSING" if probability <= 0.4 else "UNCERTAIN")
        warnings = (
            "This bounded estimate is not a calibrated forecast or profitability claim.",
        )
        return SpecialistAssessment(
            self.name,
            inputs.symbol.strip().upper(),
            status,
            round(probability, 4),
            round(inputs.mean_confidence, 2),
            (
                f"Supporting/opposing signals: {inputs.supporting_signals}/{inputs.opposing_signals}.",
                f"Neutral signals recorded: {inputs.neutral_signals}.",
            ),
            warnings,
            inputs.observed_at.astimezone(timezone.utc),
        )

    @staticmethod
    def _validate(inputs: ProbabilityInputs) -> None:
        if not isinstance(inputs, ProbabilityInputs) or not inputs.symbol.strip():
            raise ValueError("Valid probability inputs and symbol are required.")
        counts = (inputs.supporting_signals, inputs.opposing_signals, inputs.neutral_signals)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("Signal counts must be non-negative integers.")
        if sum(counts) == 0:
            raise ValueError("At least one signal is required.")
        if isinstance(inputs.mean_confidence, bool) or not isfinite(inputs.mean_confidence) or not 0 <= inputs.mean_confidence <= 100:
            raise ValueError("Mean confidence must be finite and between 0 and 100.")
        if inputs.observed_at.tzinfo is None:
            raise ValueError("Probability timestamp must be timezone-aware.")

