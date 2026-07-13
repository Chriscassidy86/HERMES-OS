"""Immutable post-trade learning explanations and recurring patterns."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistOutcomeExplanation:
    source: str
    predicted_direction: str
    confidence: float
    correct: bool
    calibration_error: float
    explanation: str


@dataclass(frozen=True)
class TradeLearningExplanation:
    trade_id: str
    outcome: str
    pnl: float
    why: tuple[str, ...]
    correct_specialists: tuple[str, ...]
    incorrect_specialists: tuple[str, ...]
    specialist_details: tuple[SpecialistOutcomeExplanation, ...]


@dataclass(frozen=True)
class RecurringMistake:
    pattern: str
    occurrences: int
    explanation: str


@dataclass(frozen=True)
class LearningExplanationReport:
    sample_size: int
    trades: tuple[TradeLearningExplanation, ...]
    confidence_brier_score: float
    calibration_explanation: str
    recurring_mistakes: tuple[RecurringMistake, ...]
    assumptions: tuple[str, ...]
    configuration_modified: bool = False
    human_review_required: bool = True

