"""
Hermes OS - Deterministic Market Feature Pipeline.

This module converts validated public OHLCV candles into an immutable
technical-feature snapshot.

Design rules:
- No network access.
- No trading or order execution.
- No invented market data.
- All calculations use the deterministic indicator engine.
- Missing source data produces None rather than fabricated values.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, log, sqrt
from statistics import pstdev
from typing import Sequence

from data_providers.public_adapters import PublicCandle

from .indicators import (
    atr,
    bollinger_bands,
    detect_swings,
    ema,
    macd,
    obv,
    relative_volume,
    rsi,
    sma,
    stochastic,
    volume_spikes,
)


@dataclass(frozen=True)
class MarketFeatures:
    """Immutable deterministic feature snapshot for one candle history."""

    symbol: str
    timeframe: str
    provider: str
    candle_count: int
    timestamp: datetime

    price: float
    reference_high: float
    reference_low: float

    sma_10: float | None
    sma_20: float | None
    ema_12: float | None
    ema_26: float | None

    rsi_14: float | None

    macd_line: float | None
    macd_signal: float | None
    macd_histogram: float | None

    stochastic_k: float | None
    stochastic_d: float | None

    atr_14: float | None

    bollinger_middle: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None

    relative_volume_20: float | None
    volume_spikes_20: int | None

    obv: float | None

    higher_highs: bool | None
    lower_lows: bool | None

    realized_volatility: float | None

    buy_volume_estimate: float | None
    sell_volume_estimate: float | None


def _validate_candles(candles: Sequence[PublicCandle]) -> tuple[PublicCandle, ...]:
    """Validate candle type, chronology, OHLC relationships, and timestamps."""

    if not isinstance(candles, (list, tuple)):
        raise ValueError("candles must be a list or tuple.")

    if not candles:
        raise ValueError("candles must not be empty.")

    validated = tuple(candles)

    previous_timestamp = None
    expected_symbol = None
    expected_timeframe = None

    for candle in validated:
        if not isinstance(candle, PublicCandle):
            raise ValueError("candles must contain PublicCandle objects.")

        if candle.timestamp.tzinfo is None:
            raise ValueError("Candle timestamps must be timezone-aware.")

        timestamp = candle.timestamp.astimezone(timezone.utc)

        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise ValueError(
                "Candle timestamps must be strictly increasing."
            )

        previous_timestamp = timestamp

        if expected_symbol is None:
            expected_symbol = candle.symbol
        elif candle.symbol != expected_symbol:
            raise ValueError("All candles must use the same symbol.")

        if expected_timeframe is None:
            expected_timeframe = candle.timeframe
        elif candle.timeframe != expected_timeframe:
            raise ValueError("All candles must use the same timeframe.")

        for name, value in (
            ("open", candle.open),
            ("high", candle.high),
            ("low", candle.low),
            ("close", candle.close),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise ValueError(
                    f"Candle {name} must be finite and greater than zero."
                )

        if candle.high < candle.low:
            raise ValueError("Candle high cannot be below low.")

        if not candle.low <= candle.open <= candle.high:
            raise ValueError("Candle open is outside the high/low range.")

        if not candle.low <= candle.close <= candle.high:
            raise ValueError("Candle close is outside the high/low range.")

        if candle.volume is not None:
            if (
                isinstance(candle.volume, bool)
                or not isinstance(candle.volume, (int, float))
                or not isfinite(candle.volume)
                or candle.volume < 0
            ):
                raise ValueError(
                    "Candle volume must be finite and non-negative."
                )

    return validated


def _realized_volatility(closes: Sequence[float]) -> float | None:
    """
    Calculate realized volatility as population standard deviation
    of consecutive logarithmic returns.

    This is intentionally not annualized because the pipeline supports
    multiple timeframes and should not silently assume a fixed bar rate.
    """

    if len(closes) < 2:
        return None

    returns = []

    for previous, current in zip(closes, closes[1:]):
        if previous <= 0 or current <= 0:
            return None

        returns.append(log(current / previous))

    if not returns:
        return None

    return pstdev(returns)


def _volume_estimates(
    candles: Sequence[PublicCandle],
) -> tuple[float | None, float | None]:
    """
    Estimate buy/sell volume using candle body position.

    A candle closing at the high is treated as 100% buy volume.
    A candle closing at the low is treated as 100% sell volume.
    Intermediate closes are split proportionally.

    This is an estimate, not exchange trade-direction data.
    """

    volumes = [candle.volume for candle in candles]

    if any(volume is None for volume in volumes):
        return (None, None)

    buy_volume = 0.0
    sell_volume = 0.0

    for candle in candles:
        volume = float(candle.volume)

        if candle.high == candle.low:
            buy_share = 0.5
        else:
            buy_share = (candle.close - candle.low) / (
                candle.high - candle.low
            )

        buy_volume += volume * buy_share
        sell_volume += volume * (1.0 - buy_share)

    return (buy_volume, sell_volume)


def build_market_features(
    candles: Sequence[PublicCandle],
) -> MarketFeatures:
    """
    Build one deterministic MarketFeatures snapshot from OHLCV history.

    The latest candle becomes the feature timestamp and current price.
    """

    validated = _validate_candles(candles)

    opens = [candle.open for candle in validated]
    highs = [candle.high for candle in validated]
    lows = [candle.low for candle in validated]
    closes = [candle.close for candle in validated]
    volumes = [candle.volume for candle in validated]

    latest = validated[-1]

    macd_result = macd(closes)
    stochastic_result = stochastic(highs, lows, closes)
    bollinger_result = bollinger_bands(closes)
    swing_result = detect_swings(closes)

    volume_available = all(volume is not None for volume in volumes)

    numeric_volumes = (
        [float(volume) for volume in volumes]
        if volume_available
        else None
    )

    if numeric_volumes is None:
        relative_volume_result = None
        volume_spikes_result = None
        obv_result = None
    else:
        relative_volume_result = relative_volume(numeric_volumes)
        volume_spikes_result = volume_spikes(numeric_volumes)
        obv_result = obv(closes, numeric_volumes)

    buy_volume, sell_volume = _volume_estimates(validated)

    return MarketFeatures(
        symbol=latest.symbol,
        timeframe=latest.timeframe,
        provider=latest.provider,
        candle_count=len(validated),
        timestamp=latest.timestamp.astimezone(timezone.utc),

        price=latest.close,
        reference_high=max(highs),
        reference_low=min(lows),

        sma_10=sma(closes, 10),
        sma_20=sma(closes, 20),
        ema_12=ema(closes, 12),
        ema_26=ema(closes, 26),

        rsi_14=rsi(closes, 14),

        macd_line=macd_result[0] if macd_result else None,
        macd_signal=macd_result[1] if macd_result else None,
        macd_histogram=macd_result[2] if macd_result else None,

        stochastic_k=(
            stochastic_result[0] if stochastic_result else None
        ),
        stochastic_d=(
            stochastic_result[1] if stochastic_result else None
        ),

        atr_14=atr(highs, lows, closes, 14),

        bollinger_middle=(
            bollinger_result[0] if bollinger_result else None
        ),
        bollinger_upper=(
            bollinger_result[1] if bollinger_result else None
        ),
        bollinger_lower=(
            bollinger_result[2] if bollinger_result else None
        ),

        relative_volume_20=relative_volume_result,
        volume_spikes_20=volume_spikes_result,

        obv=obv_result,

        higher_highs=swing_result[0] if swing_result else None,
        lower_lows=swing_result[1] if swing_result else None,

        realized_volatility=_realized_volatility(closes),

        buy_volume_estimate=buy_volume,
        sell_volume_estimate=sell_volume,
    )
