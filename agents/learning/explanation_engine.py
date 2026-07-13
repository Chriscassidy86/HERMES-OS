"""Deterministic post-trade explanations; never updates configuration."""

from collections import Counter
from datetime import datetime
from math import isfinite
from statistics import mean

from models.learning_explanation import (
    LearningExplanationReport,
    RecurringMistake,
    SpecialistOutcomeExplanation,
    TradeLearningExplanation,
)
from models.performance import TradeOutcome


class LearningExplanationEngine:
    def explain(self, outcomes: tuple[TradeOutcome, ...]) -> LearningExplanationReport:
        if not outcomes:
            raise ValueError("Closed paper outcomes are required for learning explanations.")
        explanations = []
        errors = []
        patterns = Counter()
        for outcome in outcomes:
            self._validate(outcome)
            winning = outcome.winning_direction
            gross = self._gross_pnl(outcome)
            details = []
            for prediction in sorted(outcome.specialist_predictions, key=lambda item: item.source):
                correct = prediction.direction == winning
                observed = 1.0 if correct else 0.0
                error = (prediction.confidence / 100.0 - observed) ** 2
                errors.append(error)
                details.append(SpecialistOutcomeExplanation(
                    prediction.source, prediction.direction, prediction.confidence, correct,
                    round(error, 6),
                    f"Predicted {prediction.direction}; realized price direction was {winning}."
                ))
                if not correct and prediction.confidence >= 70:
                    patterns["OVERCONFIDENT_INCORRECT_SPECIALIST"] += 1
            if outcome.pnl > 0:
                status = "SUCCESS"
                why = ("Price movement supported the paper position after fees.",
                       f"Directional gross result {gross:.4f} exceeded fees {outcome.fees:.4f}.")
            elif outcome.pnl < 0:
                status = "LOSS"
                if gross <= 0:
                    patterns["POSITION_OPPOSED_REALIZED_MOVE"] += 1
                    cause = "Realized price movement opposed the paper position."
                else:
                    patterns["FEES_OVERWHELMED_GROSS_GAIN"] += 1
                    cause = "Fees exceeded the favorable directional gross result."
                why = (cause, f"Directional gross result was {gross:.4f}; fees were {outcome.fees:.4f}.")
            else:
                status = "FLAT"
                why = ("Directional gross result and fees produced a flat paper outcome.",)
            correct_sources = tuple(item.source for item in details if item.correct)
            incorrect_sources = tuple(item.source for item in details if not item.correct)
            explanations.append(TradeLearningExplanation(
                outcome.trade_id, status, round(outcome.pnl, 6), why,
                correct_sources, incorrect_sources, tuple(details)
            ))
        recurring = tuple(
            RecurringMistake(pattern, count, self._pattern_explanation(pattern))
            for pattern, count in sorted(patterns.items()) if count >= 2
        )
        brier = round(mean(errors), 6) if errors else 0.0
        calibration = (
            f"Mean specialist Brier error is {brier:.4f} across {len(errors)} supplied predictions."
            if errors else "No specialist predictions were supplied; calibration is unavailable."
        )
        return LearningExplanationReport(
            len(outcomes), tuple(explanations), brier, calibration, recurring,
            ("Only closed PAPER outcomes are analyzed.",
             "Observed patterns do not establish future profitability.",
             "Any proposed strategy or weight change requires separate human approval."),
        )

    @staticmethod
    def _gross_pnl(outcome):
        multiplier = 1 if outcome.direction == "LONG" else -1
        return (outcome.exit_price - outcome.entry_price) * outcome.quantity * multiplier

    @staticmethod
    def _pattern_explanation(pattern):
        values = {
            "OVERCONFIDENT_INCORRECT_SPECIALIST": "Incorrect specialist directions repeatedly carried at least 70% confidence.",
            "POSITION_OPPOSED_REALIZED_MOVE": "Paper positions repeatedly opposed the realized price direction.",
            "FEES_OVERWHELMED_GROSS_GAIN": "Favorable gross moves repeatedly failed to cover simulated fees.",
        }
        return values[pattern]

    @staticmethod
    def _validate(outcome):
        if not isinstance(outcome, TradeOutcome) or not outcome.trade_id.strip() or not outcome.symbol.strip():
            raise ValueError("Valid closed paper trade outcomes are required.")
        if outcome.direction not in {"LONG", "SHORT"}:
            raise ValueError("Learning outcome direction must be LONG or SHORT.")
        numbers = (outcome.entry_price, outcome.exit_price, outcome.quantity, outcome.fees)
        if any(isinstance(value, bool) or not isfinite(value) for value in numbers):
            raise ValueError("Learning outcome numbers must be finite.")
        if outcome.entry_price <= 0 or outcome.exit_price <= 0 or outcome.quantity <= 0 or outcome.fees < 0:
            raise ValueError("Learning outcome price, quantity, or fees are invalid.")
        if not isinstance(outcome.opened_at, datetime) or not isinstance(outcome.closed_at, datetime):
            raise ValueError("Learning outcome timestamps are required.")
        if outcome.opened_at.tzinfo is None or outcome.closed_at.tzinfo is None or outcome.closed_at < outcome.opened_at:
            raise ValueError("Learning outcome timestamps are invalid.")
        for prediction in outcome.specialist_predictions:
            if (not prediction.source.strip() or prediction.direction not in {"LONG", "SHORT", "WAIT"}
                    or not isfinite(prediction.confidence) or not 0 <= prediction.confidence <= 100):
                raise ValueError("Specialist prediction is malformed.")

