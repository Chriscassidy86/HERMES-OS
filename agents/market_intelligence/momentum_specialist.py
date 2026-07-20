"""
===============================================================================

Hermes OS

File:
momentum_specialist.py

Purpose:
Momentum Specialist for the Market Intelligence framework. Evaluates only the
momentum domain: RSI, MACD, and Stochastic oscillator.

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
from agents.market_intelligence.indicators import macd, rsi, stochastic
from models.market_intelligence import (
    AgentStatus,
    MarketIntelligenceReport,
    MomentumInputs,
)


class MomentumSpecialist(MarketIntelligenceSpecialist):
    """
    Market Intelligence Momentum Specialist.

    Evaluates momentum using:
      - RSI (Relative Strength Index)
      - MACD (Moving Average Convergence Divergence)
      - Stochastic Oscillator (%K, %D)

    Produces an advisory-only ``MarketIntelligenceReport``.
    """

    VERSION = "1.0.0"
    SUPPORTED_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD")
    SUPPORTED_TIMEFRAMES = ("1H", "4H", "1D")

    #: RSI period.
    RSI_PERIOD = 14
    #: RSI overbought threshold.
    RSI_OVERBOUGHT = 70.0
    #: RSI oversold threshold.
    RSI_OVERSOLD = 30.0
    #: MACD fast period.
    MACD_FAST = 12
    #: MACD slow period.
    MACD_SLOW = 26
    #: MACD signal period.
    MACD_SIGNAL = 9
    #: Stochastic %K period.
    STOCH_K_PERIOD = 14
    #: Stochastic %D period.
    STOCH_D_PERIOD = 3
    #: Stochastic overbought threshold.
    STOCH_OVERBOUGHT = 80.0
    #: Stochastic oversold threshold.
    STOCH_OVERSOLD = 20.0

    def __init__(self):
        super().__init__("Momentum Intelligence Specialist")
        self._set_status(AgentStatus.ONLINE)

    def analyze(self, inputs: MomentumInputs) -> MarketIntelligenceReport:
        """
        Analyze momentum evidence from validated candle inputs.

        Args:
            inputs: ``MomentumInputs`` with symbol, timeframe,
                observed_at, and a tuple of validated candles.

        Returns:
            An immutable, advisory-only ``MarketIntelligenceReport``.

        Raises:
            ValueError: If inputs are invalid or insufficient.
        """
        if not isinstance(inputs, MomentumInputs):
            raise ValueError("MomentumSpecialist requires MomentumInputs.")

        closes = [c.close for c in inputs.candles]
        highs = [c.high for c in inputs.candles]
        lows = [c.low for c in inputs.candles]
        now = datetime.now(timezone.utc)

        evidence: list[str] = []
        conflicting: list[str] = []
        warnings: list[str] = []
        bullish_signals = 0
        bearish_signals = 0

        # --- RSI analysis ---
        rsi_val = rsi(closes, self.RSI_PERIOD)
        if rsi_val is not None:
            if rsi_val >= self.RSI_OVERBOUGHT:
                bearish_signals += 1
                evidence.append(
                    f"RSI ({rsi_val:.2f}) is overbought "
                    f"(>= {self.RSI_OVERBOUGHT})."
                )
            elif rsi_val <= self.RSI_OVERSOLD:
                bullish_signals += 1
                evidence.append(
                    f"RSI ({rsi_val:.2f}) is oversold "
                    f"(<= {self.RSI_OVERSOLD})."
                )
            else:
                evidence.append(
                    f"RSI ({rsi_val:.2f}) is neutral "
                    f"({self.RSI_OVERSOLD} - {self.RSI_OVERBOUGHT})."
                )
        else:
            warnings.append("Insufficient data for RSI analysis.")

        # --- MACD analysis ---
        macd_result = macd(
            closes,
            fast=self.MACD_FAST,
            slow=self.MACD_SLOW,
            signal=self.MACD_SIGNAL,
        )
        if macd_result is not None:
            macd_line, signal_line, histogram = macd_result
            if macd_line > signal_line:
                bullish_signals += 1
                evidence.append(
                    f"MACD line ({macd_line:.4f}) is above signal "
                    f"({signal_line:.4f}); histogram {histogram:.4f}."
                )
            elif macd_line < signal_line:
                bearish_signals += 1
                evidence.append(
                    f"MACD line ({macd_line:.4f}) is below signal "
                    f"({signal_line:.4f}); histogram {histogram:.4f}."
                )
            else:
                conflicting.append("MACD line equals signal line.")
        else:
            warnings.append("Insufficient data for MACD analysis.")

        # --- Stochastic analysis ---
        stoch_result = stochastic(
            highs,
            lows,
            closes,
            k_period=self.STOCH_K_PERIOD,
            d_period=self.STOCH_D_PERIOD,
        )
        if stoch_result is not None:
            k_val, d_val = stoch_result
            if k_val >= self.STOCH_OVERBOUGHT:
                bearish_signals += 1
                evidence.append(
                    f"Stochastic %K ({k_val:.2f}) is overbought "
                    f"(>= {self.STOCH_OVERBOUGHT})."
                )
            elif k_val <= self.STOCH_OVERSOLD:
                bullish_signals += 1
                evidence.append(
                    f"Stochastic %K ({k_val:.2f}) is oversold "
                    f"(<= {self.STOCH_OVERSOLD})."
                )
            else:
                evidence.append(
                    f"Stochastic %K ({k_val:.2f}) is neutral; "
                    f"%D {d_val:.2f}."
                )
            if k_val > d_val:
                bullish_signals += 1
                evidence.append(
                    f"Stochastic %K ({k_val:.2f}) crossed above "
                    f"%D ({d_val:.2f})."
                )
            elif k_val < d_val:
                bearish_signals += 1
                evidence.append(
                    f"Stochastic %K ({k_val:.2f}) crossed below "
                    f"%D ({d_val:.2f})."
                )
        else:
            warnings.append("Insufficient data for Stochastic analysis.")

        # --- Confidence and explanation ---
        total = bullish_signals + bearish_signals
        if total == 0:
            confidence = 0.20
            explanation = (
                "No clear momentum signal from RSI, MACD, or Stochastic. "
                "Evidence is insufficient or neutral."
            )
        else:
            dominant = max(bullish_signals, bearish_signals)
            confidence = min(0.35 + 0.15 * dominant, 0.80)
            if bullish_signals > bearish_signals:
                direction = "bullish"
            elif bearish_signals > bullish_signals:
                direction = "bearish"
            else:
                direction = "mixed"
                confidence = min(confidence, 0.45)
            explanation = (
                f"Momentum evidence is {direction} with {bullish_signals} "
                f"bullish and {bearish_signals} bearish signals from "
                f"RSI, MACD, and Stochastic."
            )

        if not evidence:
            evidence = ("No momentum evidence available.",)

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
