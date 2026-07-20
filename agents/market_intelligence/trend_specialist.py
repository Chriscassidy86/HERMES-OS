"""
===============================================================================

Hermes OS

File:
trend_specialist.py

Purpose:
Trend Specialist for the Market Intelligence framework. Evaluates only the
trend domain: EMA, SMA, and higher-highs / lower-lows structure.

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
from agents.market_intelligence.indicators import detect_swings, ema, sma
from models.market_intelligence import (
    AgentStatus,
    MarketIntelligenceReport,
    TrendInputs,
)


class TrendSpecialist(MarketIntelligenceSpecialist):
    """
    Market Intelligence Trend Specialist.

    Evaluates directional trend using:
      - EMA (short and long)
      - SMA (short and long)
      - Higher highs / lower lows swing structure

    Produces an advisory-only ``MarketIntelligenceReport``.
    """

    VERSION = "1.0.0"
    SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD")
    SUPPORTED_TIMEFRAMES = ("1H", "4H", "1D")

    #: Short EMA period.
    EMA_SHORT = 12
    #: Long EMA period.
    EMA_LONG = 26
    #: Short SMA period.
    SMA_SHORT = 10
    #: Long SMA period.
    SMA_LONG = 20
    #: Lookback for swing detection.
    SWING_LOOKBACK = 20

    def __init__(self):
        super().__init__("Trend Intelligence Specialist")
        self._set_status(AgentStatus.ONLINE)

    def analyze(self, inputs: TrendInputs) -> MarketIntelligenceReport:
        """
        Analyze trend evidence from validated candle inputs.

        Args:
            inputs: ``TrendInputs`` with symbol, timeframe, observed_at,
                and a tuple of validated candles.

        Returns:
            An immutable, advisory-only ``MarketIntelligenceReport``.

        Raises:
            ValueError: If inputs are invalid or insufficient.
        """
        if not isinstance(inputs, TrendInputs):
            raise ValueError("TrendSpecialist requires TrendInputs.")

        closes = [c.close for c in inputs.candles]
        now = datetime.now(timezone.utc)

        evidence: list[str] = []
        conflicting: list[str] = []
        warnings: list[str] = []
        bullish_signals = 0
        bearish_signals = 0

        # --- EMA analysis ---
        ema_short = ema(closes, self.EMA_SHORT)
        ema_long = ema(closes, self.EMA_LONG)
        if ema_short is not None and ema_long is not None:
            if ema_short > ema_long:
                bullish_signals += 1
                evidence.append(
                    f"EMA{self.EMA_SHORT} ({ema_short:.2f}) is above "
                    f"EMA{self.EMA_LONG} ({ema_long:.2f})."
                )
            elif ema_short < ema_long:
                bearish_signals += 1
                evidence.append(
                    f"EMA{self.EMA_SHORT} ({ema_short:.2f}) is below "
                    f"EMA{self.EMA_LONG} ({ema_long:.2f})."
                )
            else:
                conflicting.append(
                    f"EMA{self.EMA_SHORT} and EMA{self.EMA_LONG} are equal."
                )
        else:
            warnings.append(
                "Insufficient data for EMA trend analysis."
            )

        # --- SMA analysis ---
        sma_short = sma(closes, self.SMA_SHORT)
        sma_long = sma(closes, self.SMA_LONG)
        if sma_short is not None and sma_long is not None:
            if sma_short > sma_long:
                bullish_signals += 1
                evidence.append(
                    f"SMA{self.SMA_SHORT} ({sma_short:.2f}) is above "
                    f"SMA{self.SMA_LONG} ({sma_long:.2f})."
                )
            elif sma_short < sma_long:
                bearish_signals += 1
                evidence.append(
                    f"SMA{self.SMA_SHORT} ({sma_short:.2f}) is below "
                    f"SMA{self.SMA_LONG} ({sma_long:.2f})."
                )
            else:
                conflicting.append(
                    f"SMA{self.SMA_SHORT} and SMA{self.SMA_LONG} are equal."
                )
        else:
            warnings.append(
                "Insufficient data for SMA trend analysis."
            )

        # --- Higher highs / lower lows ---
        swings = detect_swings(closes, self.SWING_LOOKBACK)
        if swings is not None:
            higher_highs, lower_lows = swings
            if higher_highs:
                bullish_signals += 1
                evidence.append("Higher highs detected in recent structure.")
            if lower_lows:
                bearish_signals += 1
                evidence.append("Lower lows detected in recent structure.")
            if higher_highs and lower_lows:
                conflicting.append(
                    "Both higher highs and lower lows present; "
                    "trend structure is mixed."
                )
        else:
            warnings.append(
                "Insufficient data for swing structure analysis."
            )

        # --- Confidence and explanation ---
        total = bullish_signals + bearish_signals
        if total == 0:
            confidence = 0.20
            explanation = (
                "No clear trend signal from EMA, SMA, or swing structure. "
                "Evidence is insufficient or conflicting."
            )
        else:
            dominant = max(bullish_signals, bearish_signals)
            confidence = min(0.40 + 0.20 * dominant, 0.85)
            if bullish_signals > bearish_signals:
                direction = "bullish"
            elif bearish_signals > bullish_signals:
                direction = "bearish"
            else:
                direction = "mixed"
                confidence = min(confidence, 0.45)
            explanation = (
                f"Trend evidence is {direction} with {bullish_signals} "
                f"bullish and {bearish_signals} bearish signals from "
                f"EMA, SMA, and swing structure."
            )

        if not evidence:
            evidence = ("No trend evidence available.",)

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
