"""
===============================================================================

Hermes OS

File:
volume_specialist.py

Purpose:
Volume Specialist for the Market Intelligence framework. Evaluates only the
volume domain: relative volume, volume spikes, and On-Balance Volume (OBV).

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
from agents.market_intelligence.indicators import (
    obv_series,
    relative_volume,
    volume_spikes,
)
from models.market_intelligence import (
    AgentStatus,
    MarketIntelligenceReport,
    VolumeInputs,
)


class VolumeSpecialist(MarketIntelligenceSpecialist):
    """
    Market Intelligence Volume Specialist.

    Evaluates volume using:
      - Relative volume (current vs. average)
      - Volume spikes (count of abnormal bars)
      - On-Balance Volume (OBV) trend

    Produces an advisory-only ``MarketIntelligenceReport``.
    """

    VERSION = "1.0.0"
    SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD")
    SUPPORTED_TIMEFRAMES = ("1H", "4H", "1D")

    #: Period for relative volume average.
    RVOL_PERIOD = 20
    #: Period for volume spike detection.
    SPIKE_PERIOD = 20
    #: Threshold multiplier for volume spikes.
    SPIKE_THRESHOLD = 2.0
    #: Relative volume threshold for "high" classification.
    RVOL_HIGH = 1.5
    #: Relative volume threshold for "low" classification.
    RVOL_LOW = 0.5

    def __init__(self):
        super().__init__("Volume Intelligence Specialist")
        self._set_status(AgentStatus.ONLINE)

    def analyze(self, inputs: VolumeInputs) -> MarketIntelligenceReport:
        """
        Analyze volume evidence from validated candle inputs.

        Args:
            inputs: ``VolumeInputs`` with symbol, timeframe, observed_at,
                and a tuple of validated candles.

        Returns:
            An immutable, advisory-only ``MarketIntelligenceReport``.

        Raises:
            ValueError: If inputs are invalid or insufficient.
        """
        if not isinstance(inputs, VolumeInputs):
            raise ValueError("VolumeSpecialist requires VolumeInputs.")

        closes = [c.close for c in inputs.candles]
        volumes = [c.volume for c in inputs.candles]
        now = datetime.now(timezone.utc)

        evidence: list[str] = []
        conflicting: list[str] = []
        warnings: list[str] = []
        bullish_signals = 0
        bearish_signals = 0

        # --- Relative volume ---
        rvol = relative_volume(volumes, self.RVOL_PERIOD)
        if rvol is not None:
            if rvol >= self.RVOL_HIGH:
                evidence.append(
                    f"Relative volume ({rvol:.2f}x) is high "
                    f"(>= {self.RVOL_HIGH}x)."
                )
            elif rvol <= self.RVOL_LOW:
                evidence.append(
                    f"Relative volume ({rvol:.2f}x) is low "
                    f"(<= {self.RVOL_LOW}x)."
                )
            else:
                evidence.append(
                    f"Relative volume ({rvol:.2f}x) is normal."
                )
        else:
            warnings.append("Insufficient data for relative volume analysis.")

        # --- Volume spikes ---
        spikes = volume_spikes(
            volumes,
            period=self.SPIKE_PERIOD,
            threshold=self.SPIKE_THRESHOLD,
        )
        if spikes is not None:
            if spikes > 0:
                evidence.append(
                    f"{spikes} volume spike(s) detected in the last "
                    f"{self.SPIKE_PERIOD} bars "
                    f"(threshold: {self.SPIKE_THRESHOLD}x average)."
                )
            else:
                evidence.append(
                    f"No volume spikes in the last {self.SPIKE_PERIOD} bars."
                )
        else:
            warnings.append("Insufficient data for volume spike analysis.")

        # --- OBV trend ---
        obv_vals = obv_series(closes, volumes)
        if len(obv_vals) >= 2:
            obv_current = obv_vals[-1]
            obv_previous = obv_vals[-2]
            if obv_current > obv_previous:
                bullish_signals += 1
                evidence.append(
                    f"OBV is rising ({obv_current:.2f} > {obv_previous:.2f})."
                )
            elif obv_current < obv_previous:
                bearish_signals += 1
                evidence.append(
                    f"OBV is falling ({obv_current:.2f} < {obv_previous:.2f})."
                )
            else:
                evidence.append(
                    f"OBV is flat ({obv_current:.2f})."
                )
        else:
            warnings.append("Insufficient data for OBV trend analysis.")

        # --- Confidence and explanation ---
        total = bullish_signals + bearish_signals
        if total == 0:
            confidence = 0.25
            explanation = (
                "Volume evidence is neutral. Relative volume, spikes, "
                "and OBV show no clear directional pressure."
            )
        else:
            dominant = max(bullish_signals, bearish_signals)
            confidence = min(0.35 + 0.15 * dominant, 0.75)
            if bullish_signals > bearish_signals:
                direction = "bullish"
            elif bearish_signals > bullish_signals:
                direction = "bearish"
            else:
                direction = "mixed"
                confidence = min(confidence, 0.45)
            explanation = (
                f"Volume evidence is {direction} with {bullish_signals} "
                f"bullish and {bearish_signals} bearish signals from "
                f"relative volume, spikes, and OBV."
            )

        if not evidence:
            evidence = ("No volume evidence available.",)

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
