"""Read-only portfolio concentration and capacity intelligence."""

from datetime import timezone
from math import isfinite

from models.specialist_intelligence import PortfolioContextInputs, SpecialistAssessment


class PortfolioContextSpecialist:
    name = "Portfolio Context Specialist"

    def analyze(self, inputs: PortfolioContextInputs) -> SpecialistAssessment:
        self._validate(inputs)
        gross_ratio = inputs.gross_exposure / inputs.equity
        symbol_ratio = inputs.symbol_exposure / inputs.equity
        cash_ratio = inputs.cash / inputs.equity
        score = max(0.0, min(1.0, 1.0 - max(gross_ratio, symbol_ratio)))
        warnings = []
        if gross_ratio > 0.75:
            warnings.append("Gross paper exposure exceeds 75% of equity.")
        if symbol_ratio > 0.25:
            warnings.append("Single-symbol paper exposure exceeds 25% of equity.")
        status = "CONSTRAINED" if warnings else "AVAILABLE"
        return SpecialistAssessment(
            self.name,
            inputs.symbol.strip().upper(),
            status,
            round(score, 4),
            100.0,
            (
                f"Cash/equity ratio is {cash_ratio:.4f}.",
                f"Gross/symbol exposure ratios are {gross_ratio:.4f}/{symbol_ratio:.4f}.",
                f"Open paper positions: {inputs.open_positions}.",
            ),
            tuple(warnings),
            inputs.observed_at.astimezone(timezone.utc),
        )

    @staticmethod
    def _validate(inputs: PortfolioContextInputs) -> None:
        if not isinstance(inputs, PortfolioContextInputs) or not inputs.symbol.strip():
            raise ValueError("Valid portfolio context and symbol are required.")
        values = (inputs.cash, inputs.equity, inputs.gross_exposure, inputs.symbol_exposure)
        if any(isinstance(value, bool) or not isfinite(value) for value in values):
            raise ValueError("Portfolio values must be finite numbers.")
        if inputs.equity <= 0 or inputs.cash < 0 or inputs.gross_exposure < 0 or inputs.symbol_exposure < 0:
            raise ValueError("Portfolio accounting values are invalid.")
        if inputs.symbol_exposure > inputs.gross_exposure:
            raise ValueError("Symbol exposure cannot exceed gross exposure.")
        if isinstance(inputs.open_positions, bool) or not isinstance(inputs.open_positions, int) or inputs.open_positions < 0:
            raise ValueError("Open positions must be a non-negative integer.")
        if inputs.observed_at.tzinfo is None:
            raise ValueError("Portfolio timestamp must be timezone-aware.")

