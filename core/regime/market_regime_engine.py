"""Explainable deterministic market-regime classification."""

from datetime import timezone
from math import isfinite

from models.market_regime import (
    InsufficientRegimeEvidence,
    MarketRegime,
    RegimeClassification,
    RegimeInputs,
)


class MarketRegimeEngine:
    def classify(self, inputs: RegimeInputs) -> RegimeClassification:
        self._validate(inputs)
        volume_ratio = inputs.volume / inputs.average_volume
        volatility_ratio = inputs.volatility / inputs.baseline_volatility
        ma_gap = (inputs.short_moving_average - inputs.long_moving_average) / inputs.long_moving_average
        price_change = (inputs.price - inputs.previous_price) / inputs.previous_price
        inside_range = inputs.reference_low <= inputs.price <= inputs.reference_high
        evidence = (
            f"Price change: {price_change:.4%}.",
            f"Short/long moving-average gap: {ma_gap:.4%}.",
            f"Volume ratio: {volume_ratio:.4f}.",
            f"Volatility ratio: {volatility_ratio:.4f}.",
            f"Buy-volume ratio: {inputs.buy_volume_ratio:.4f}.",
        )
        regime, strength, explanation = self._rules(
            inputs, volume_ratio, volatility_ratio, ma_gap, inside_range
        )
        uncertainty = ["Classification uses supplied historical observations, not future outcomes."]
        if abs(ma_gap) < 0.015:
            uncertainty.append("Moving-average separation is near a regime boundary.")
        if 0.9 < volume_ratio < 1.2:
            uncertainty.append("Volume is not strongly differentiated from its baseline.")
        confidence = min(95.0, max(50.0, 55.0 + strength * 40.0))
        return RegimeClassification(
            inputs.symbol.strip().upper(), regime, round(confidence, 2), evidence,
            explanation, tuple(uncertainty), inputs.observed_at.astimezone(timezone.utc)
        )

    @staticmethod
    def _rules(inputs, volume_ratio, volatility_ratio, ma_gap, inside_range):
        if inputs.price > inputs.reference_high and volume_ratio >= 1.2:
            strength = min(1.0, (inputs.price / inputs.reference_high - 1) * 20 + (volume_ratio - 1))
            return MarketRegime.BREAKOUT, strength, "Price broke above the reference range with confirming volume."
        if inputs.price < inputs.reference_low and volume_ratio >= 1.2:
            strength = min(1.0, (1 - inputs.price / inputs.reference_low) * 20 + (volume_ratio - 1))
            return MarketRegime.BREAKDOWN, strength, "Price broke below the reference range with confirming volume."
        if volatility_ratio >= 1.5:
            return MarketRegime.HIGH_VOLATILITY, min(1.0, volatility_ratio / 2), "Volatility is materially above its validated baseline."
        if volatility_ratio <= 0.6:
            return MarketRegime.LOW_VOLATILITY, min(1.0, 1 - volatility_ratio + 0.4), "Volatility is materially below its validated baseline."
        if inside_range and volume_ratio >= 1.2 and inputs.buy_volume_ratio >= 0.6:
            return MarketRegime.ACCUMULATION, min(1.0, volume_ratio - 0.4), "Elevated in-range volume is dominated by supplied buy-side volume."
        if inside_range and volume_ratio >= 1.2 and inputs.buy_volume_ratio <= 0.4:
            return MarketRegime.DISTRIBUTION, min(1.0, volume_ratio - 0.4), "Elevated in-range volume is dominated by supplied sell-side volume."
        if ma_gap >= 0.01 and inputs.price > inputs.short_moving_average:
            return MarketRegime.BULL_TREND, min(1.0, ma_gap * 20 + 0.4), "Price and moving averages are aligned upward."
        if ma_gap <= -0.01 and inputs.price < inputs.short_moving_average:
            return MarketRegime.BEAR_TREND, min(1.0, abs(ma_gap) * 20 + 0.4), "Price and moving averages are aligned downward."
        if inside_range and abs(ma_gap) <= 0.005 and abs(inputs.price / inputs.previous_price - 1) <= 0.01:
            return MarketRegime.SIDEWAYS, 0.65, "Price and moving averages remain compressed inside the reference range."
        return MarketRegime.TRANSITION, 0.5, "Validated signals do not yet form another stable regime."

    @staticmethod
    def _validate(inputs: RegimeInputs) -> None:
        if not isinstance(inputs, RegimeInputs) or not inputs.symbol.strip():
            raise InsufficientRegimeEvidence("Regime inputs and symbol are required.")
        values = (
            inputs.price, inputs.previous_price, inputs.short_moving_average,
            inputs.long_moving_average, inputs.volume, inputs.average_volume,
            inputs.volatility, inputs.baseline_volatility, inputs.reference_high,
            inputs.reference_low, inputs.buy_volume_ratio,
        )
        if any(isinstance(value, bool) or not isfinite(value) for value in values):
            raise InsufficientRegimeEvidence("Regime evidence must contain finite numbers.")
        positive = values[:10]
        if any(value <= 0 for value in positive):
            raise InsufficientRegimeEvidence("Regime price, volume, volatility, and range evidence must be positive.")
        if inputs.reference_high <= inputs.reference_low:
            raise InsufficientRegimeEvidence("Reference range is contradictory.")
        if not 0 <= inputs.buy_volume_ratio <= 1:
            raise InsufficientRegimeEvidence("Buy-volume ratio must be between zero and one.")
        if inputs.observed_at.tzinfo is None:
            raise InsufficientRegimeEvidence("Regime timestamp must be timezone-aware.")

