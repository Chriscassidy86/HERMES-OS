"""
===============================================================================

Hermes OS

File:
volatility_specialist.py

Purpose:
Volatility Specialist for the Market Intelligence framework. Evaluates only
the volatility domain: ATR, Bollinger Bands, and volatility regime
classification.

This specialist is advisory-only. It produces ``MarketIntelligenceReport``
objects and never places trades, accesses exchanges, mutates portfolios,
or bypasses the Risk Manager.

Author:
Hermes Quant Labs

Foundation:
VIII - Market Intelligence Framework, Phase 2

===============================================================================
"""

from datetime import datetime, timezone

from agents.market_intelligence.base import MarketIntelligenceSpecialist
from agents.market_intelligence.indicators import atr, bollinger_bands
from models.market_intelligence import (
    AgentStatus,
    MarketIntelligenceReport,
    VolatilityInputs,
)


class VolatilitySpecialist(MarketIntelligenceSpecialist):
    """
    Market Intelligence Volatility Specialist.

    Evaluates volatility using:
      - ATR (Average True Range)
      - Bollinger Bands (width and position)
      - Volatility regime classification (low / normal / high)

    Produces an advisory-only ``MarketIntelligenceReport``.
    """

    VERSION = "1.0.0"
    SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD")
    SUPPORTED_TIMEFRAMES = ("1H", "4H", "1D")

    #: ATR period.
    ATR_PERIOD = 14
    #: Bollinger Bands period.
    BB_PERIOD = 20
    #: Bollinger Bands standard deviation multiplier.
    BB_STD_DEV = 2.0
    #: ATR as fraction of price for "high" volatility regime.
    ATR_HIGH_FRACTION = 0.03
    #: ATR as fraction of price for "low" volatility regime.
    ATR_LOW_FRACTION = 0.01
    #: Bollinger Band width (as fraction of middle) for "high" volatility.
    BB_WIDTH_HIGH = 0.10
    #: Bollinger Band width (as fraction of middle) for "low" volatility.
    BB_WIDTH_LOW = 0.03

    def __init__(self):
        super().__init__("Volatility Intelligence Specialist")
        self._set_status(AgentStatus.ONLINE)

    def analyze(self, inputs: VolatilityInputs) -> MarketIntelligenceReport:
        """
        Analyze volatility evidence from validated candle inputs.

        Args:
            inputs: ``VolatilityInputs`` with symbol, timeframe,
                observed_at, and a tuple of validated candles.

        Returns:
            An immutable, advisory-only ``MarketIntelligenceReport``.

        Raises:
            ValueError: If inputs are invalid or insufficient.
        """
        if not isinstance(inputs, VolatilityInputs):
            raise ValueError("VolatilitySpecialist requires VolatilityInputs.")

        closes = [c.close for c in inputs.candles]
        highs = [c.high for c in inputs.candles]
        lows = [c.low for c in inputs.candles]
        last_close = closes[-1]
        now = datetime.now(timezone.utc)

        evidence: list[str] = []
        conflicting: list[str] = []
        warnings: list[str] = []
        regime_votes: list[str] = []

        # --- ATR analysis ---
        atr_val = atr(highs, lows, closes, self.ATR_PERIOD)
        if atr_val is not None and last_close > 0:
            atr_fraction = atr_val / last_close
            if atr_fraction >= self.ATR_HIGH_FRACTION:
                regime_votes.append("high")
                evidence.append(
                    f"ATR ({atr_val:.2f}) is {atr_fraction:.4f} of price "
                    f"(>= {self.ATR_HIGH_FRACTION}); high volatility."
                )
            elif atr_fraction <= self.ATR_LOW_FRACTION:
                regime_votes.append("low")
                evidence.append(
                    f"ATR ({atr_val:.2f}) is {atr_fraction:.4f} of price "
                    f"(<= {self.ATR_LOW_FRACTION}); low volatility."
                )
            else:
                regime_votes.append("normal")
                evidence.append(
                    f"ATR ({atr_val:.2f}) is {atr_fraction:.4f} of price; "
                    f"normal volatility."
                )
        else:
            warnings.append("Insufficient data for ATR analysis.")

        # --- Bollinger Bands analysis ---
        bb = bollinger_bands(
            closes,
            period=self.BB_PERIOD,
            std_dev=self.BB_STD_DEV,
        )
        if bb is not None:
            middle, upper, lower = bb
            band_width = upper - lower
            if middle > 0:
                width_fraction = band_width / middle
                if width_fraction >= self.BB_WIDTH_HIGH:
                    regime_votes.append("high")
                    evidence.append(
                        f"Bollinger Band width ({width_fraction:.4f}) is "
                        f"high (>= {self.BB_WIDTH_HIGH})."
                    )
                elif width_fraction <= self.BB_WIDTH_LOW:
                    regime_votes.append("low")
                    evidence.append(
                        f"Bollinger Band width ({width_fraction:.4f}) is "
                        f"low (<= {self.BB_WIDTH_LOW})."
                    )
                else:
                    regime_votes.append("normal")
                    evidence.append(
                        f"Bollinger Band width ({width_fraction:.4f}) is "
                        f"normal."
                    )
            # Position of price within bands
            if band_width > 0:
                position = (last_close - lower) / band_width
                if position >= 1.0:
                    evidence.append(
                        f"Price ({last_close:.2f}) is at or above the "
                        f"upper Bollinger Band ({upper:.2f})."
                    )
                elif position <= 0.0:
                    evidence.append(
                        f"Price ({last_close:.2f}) is at or below the "
                        f"lower Bollinger Band ({lower:.2f})."
                    )
                else:
                    evidence.append(
                        f"Price ({last_close:.2f}) is within Bollinger "
                        f"Bands [{lower:.2f}, {upper:.2f}]."
                    )
        else:
            warnings.append("Insufficient data for Bollinger Bands analysis.")

        # --- Volatility regime classification ---
        if regime_votes:
            high_count = regime_votes.count("high")
            low_count = regime_votes.count("low")
            normal_count = regime_votes.count("normal")
            if high_count > low_count and high_count >= normal_count:
                regime = "high"
                confidence = 0.75
            elif low_count > high_count and low_count >= normal_count:
                regime = "low"
                confidence = 0.70
            else:
                regime = "normal"
                confidence = 0.60
            explanation = (
                f"Volatility regime is {regime} based on ATR and "
                f"Bollinger Bands. ATR vote: {regime_votes[0] if atr_val is not None else 'n/a'}; "
                f"BB vote: {regime_votes[-1] if bb is not None else 'n/a'}."
            )
        else:
            regime = "indeterminate"
            confidence = 0.20
            explanation = (
                "Volatility regime is indeterminate due to insufficient "
                "data from ATR and Bollinger Bands."
            )

        if not evidence:
            evidence = ("No volatility evidence available.",)

        return MarketIntelligenceReport.create(
            agent_name=self.name,
            symbol=inputs.symbol,
            timeframe=inputs.timeframe,
            observed_at=inputs.observed_at,
            confidence=confidence,
            evidence=tuple(evidence),
            conflicting_evidence=tuple(conflicting),
            warnings=tuple(warnings),
            explanation=explanation,
            now=now,
        )
