"""Validated advisory liquidity intelligence with no exchange capability."""

from datetime import timezone
from math import isfinite

from models.specialist_intelligence import LiquidityInputs, SpecialistAssessment


class LiquiditySpecialist:
    name = "Liquidity Specialist"

    def analyze(self, inputs: LiquidityInputs) -> SpecialistAssessment:
        self._validate(inputs)
        midpoint = (inputs.bid_price + inputs.ask_price) / 2
        spread_bps = (inputs.ask_price - inputs.bid_price) / midpoint * 10_000
        total_depth = inputs.bid_depth + inputs.ask_depth
        imbalance = (inputs.bid_depth - inputs.ask_depth) / total_depth
        score = max(0.0, min(1.0, 1.0 - spread_bps / 100.0))
        status = "HEALTHY" if spread_bps <= 20 and total_depth > 0 else "THIN"
        warnings = () if status == "HEALTHY" else ("Liquidity is thin; do not infer executable size.",)
        return SpecialistAssessment(
            self.name,
            inputs.symbol.strip().upper(),
            status,
            round(score, 4),
            round(min(95.0, 60.0 + score * 35.0), 2),
            (
                f"Quoted spread is {spread_bps:.2f} bps.",
                f"Displayed depth imbalance is {imbalance:.4f}.",
            ),
            warnings,
            inputs.observed_at.astimezone(timezone.utc),
        )

    @staticmethod
    def _validate(inputs: LiquidityInputs) -> None:
        if not isinstance(inputs, LiquidityInputs):
            raise ValueError("Liquidity inputs are required.")
        if not inputs.symbol.strip():
            raise ValueError("Liquidity symbol is required.")
        values = (inputs.bid_price, inputs.ask_price, inputs.bid_depth, inputs.ask_depth)
        if any(isinstance(value, bool) or not isfinite(value) for value in values):
            raise ValueError("Liquidity values must be finite numbers.")
        if inputs.bid_price <= 0 or inputs.ask_price <= 0 or inputs.ask_price < inputs.bid_price:
            raise ValueError("Liquidity quotes are malformed or crossed.")
        if inputs.bid_depth < 0 or inputs.ask_depth < 0 or inputs.bid_depth + inputs.ask_depth <= 0:
            raise ValueError("Liquidity depth must be non-negative and non-empty.")
        if inputs.observed_at.tzinfo is None:
            raise ValueError("Liquidity timestamp must be timezone-aware.")

