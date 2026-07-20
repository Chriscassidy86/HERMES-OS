"""
===============================================================================

Hermes OS

File:
indicators.py

Purpose:
Deterministic, pure-function technical indicator implementations for the
Market Intelligence specialists. All functions are stateless, accept plain
numeric sequences, and return either a float, a tuple, or ``None`` when
there is insufficient data.

No function in this module performs I/O, networking, or mutation. These
implementations are advisory calculation helpers only. They do not produce
trading signals, buy/sell directives, or portfolio actions.

Author:
Hermes Quant Labs

Foundation:
VIII - Market Intelligence Framework

===============================================================================
"""

from math import isfinite, sqrt
from typing import Sequence


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_series(values: Sequence[float], name: str) -> None:
    """Validate that a sequence contains finite numeric values."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple.")
    for v in values:
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not isfinite(v)
        ):
            raise ValueError(f"{name} must contain finite numeric values.")


def _validate_period(period: int, name: str = "period") -> None:
    """Validate that a period is a positive integer."""
    if not isinstance(period, int) or isinstance(period, bool) or period <= 0:
        raise ValueError(f"{name} must be a positive integer.")


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------


def sma(values: Sequence[float], period: int) -> float | None:
    """
    Return the simple moving average over the last ``period`` values.

    Returns ``None`` if there are fewer than ``period`` values.
    """
    _validate_period(period)
    _validate_series(values, "values")
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def _ema_series(values: Sequence[float], period: int) -> list[float]:
    """
    Return the full EMA series seeded with the SMA of the first ``period``
    values.

    The returned list has length ``len(values) - period + 1`` (or 0 if
    there are fewer than ``period`` values). Element ``k`` corresponds to
    the EMA at index ``period - 1 + k`` in the original series.
    """
    n = len(values)
    if n < period:
        return []
    multiplier = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    result = [seed]
    current = seed
    for i in range(period, n):
        current = (values[i] - current) * multiplier + current
        result.append(current)
    return result


def ema(values: Sequence[float], period: int) -> float | None:
    """
    Return the exponential moving average over the series.

    Returns ``None`` if there are fewer than ``period`` values.
    """
    _validate_period(period)
    _validate_series(values, "values")
    series = _ema_series(values, period)
    if not series:
        return None
    return series[-1]


# ---------------------------------------------------------------------------
# Momentum indicators
# ---------------------------------------------------------------------------


def rsi(closes: Sequence[float], period: int = 14) -> float | None:
    """
    Return the Relative Strength Index using Wilder's smoothing.

    Returns ``None`` if there are fewer than ``period + 1`` closes.
    """
    _validate_period(period)
    _validate_series(closes, "closes")
    n = len(closes)
    if n < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(c, 0.0) for c in changes]
    losses = [max(-c, 0.0) for c in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float, float, float] | None:
    """
    Return the MACD line, signal line, and histogram.

    Returns ``(macd_line, signal_line, histogram)`` or ``None`` if there
    is insufficient data (fewer than ``slow + signal - 1`` closes).
    """
    _validate_period(fast, "fast")
    _validate_period(slow, "slow")
    _validate_period(signal, "signal")
    if fast >= slow:
        raise ValueError("fast period must be less than slow period.")
    _validate_series(closes, "closes")
    n = len(closes)
    if n < slow:
        return None
    fast_series = _ema_series(closes, fast)
    slow_series = _ema_series(closes, slow)
    offset = slow - fast
    macd_line = [
        fast_series[i + offset] - slow_series[i]
        for i in range(len(slow_series))
    ]
    if len(macd_line) < signal:
        return None
    signal_series = _ema_series(macd_line, signal)
    if not signal_series:
        return None
    macd_val = macd_line[-1]
    signal_val = signal_series[-1]
    histogram = macd_val - signal_val
    return (macd_val, signal_val, histogram)


def stochastic(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[float, float] | None:
    """
    Return the Stochastic Oscillator (%K, %D).

    %K is the raw stochastic over the last ``k_period`` periods.
    %D is the simple moving average of %K over ``d_period`` periods.

    Returns ``None`` if there is insufficient data (fewer than
    ``k_period + d_period - 1`` bars).
    """
    _validate_period(k_period, "k_period")
    _validate_period(d_period, "d_period")
    _validate_series(highs, "highs")
    _validate_series(lows, "lows")
    _validate_series(closes, "closes")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal length.")
    n = len(closes)
    if n < k_period + d_period - 1:
        return None
    k_values: list[float] = []
    for i in range(d_period):
        end = n - d_period + 1 + i
        window_highs = highs[end - k_period : end]
        window_lows = lows[end - k_period : end]
        highest_high = max(window_highs)
        lowest_low = min(window_lows)
        close = closes[end - 1]
        if highest_high == lowest_low:
            k_values.append(50.0)
        else:
            k_values.append(
                (close - lowest_low) / (highest_high - lowest_low) * 100.0
            )
    k = k_values[-1]
    d = sum(k_values) / d_period
    return (k, d)


# ---------------------------------------------------------------------------
# Volatility indicators
# ---------------------------------------------------------------------------


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    """
    Return the Average True Range using simple averaging of True Range.

    Returns ``None`` if there are fewer than ``period + 1`` bars (TR
    requires a previous close).
    """
    _validate_period(period)
    _validate_series(highs, "highs")
    _validate_series(lows, "lows")
    _validate_series(closes, "closes")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal length.")
    n = len(closes)
    if n < period + 1:
        return None
    tr_values: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_values.append(tr)
    if len(tr_values) < period:
        return None
    return sum(tr_values[-period:]) / period


def bollinger_bands(
    closes: Sequence[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[float, float, float] | None:
    """
    Return the Bollinger Bands as ``(middle, upper, lower)``.

    The middle band is the SMA. The upper and lower bands are
    ``middle ± std_dev * population_std``.

    Returns ``None`` if there are fewer than ``period`` closes.
    """
    _validate_period(period)
    _validate_series(closes, "closes")
    if not isinstance(std_dev, (int, float)) or isinstance(std_dev, bool):
        raise ValueError("std_dev must be a number.")
    if not isfinite(std_dev) or std_dev < 0:
        raise ValueError("std_dev must be finite and non-negative.")
    n = len(closes)
    if n < period:
        return None
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = sqrt(variance)
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return (middle, upper, lower)


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------


def relative_volume(
    volumes: Sequence[float],
    period: int = 20,
) -> float | None:
    """
    Return the ratio of the latest volume to the average of the previous
    ``period`` volumes.

    Returns ``None`` if there are fewer than ``period + 1`` volumes or
    if the average is zero.
    """
    _validate_period(period)
    _validate_series(volumes, "volumes")
    n = len(volumes)
    if n < period + 1:
        return None
    avg = sum(volumes[-(period + 1) : -1]) / period
    if avg == 0:
        return None
    return volumes[-1] / avg


def volume_spikes(
    volumes: Sequence[float],
    period: int = 20,
    threshold: float = 2.0,
) -> int | None:
    """
    Count how many of the last ``period`` volumes exceed
    ``threshold * average`` of the preceding ``period`` volumes.

    Returns ``None`` if there is insufficient data or the average is zero.
    """
    _validate_period(period)
    _validate_series(volumes, "volumes")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("threshold must be a number.")
    if not isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive.")
    n = len(volumes)
    if n < period * 2:
        return None
    avg = sum(volumes[-(period * 2) : -period]) / period
    if avg == 0:
        return None
    recent = volumes[-period:]
    return sum(1 for v in recent if v > threshold * avg)


def obv(
    closes: Sequence[float],
    volumes: Sequence[float],
) -> float | None:
    """
    Return the final cumulative On-Balance Volume value.

    Returns ``None`` if there are fewer than 2 bars.
    """
    _validate_series(closes, "closes")
    _validate_series(volumes, "volumes")
    if len(closes) != len(volumes):
        raise ValueError("closes and volumes must have equal length.")
    n = len(closes)
    if n < 2:
        return None
    result = 0.0
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            result += volumes[i]
        elif closes[i] < closes[i - 1]:
            result -= volumes[i]
    return result


def obv_series(
    closes: Sequence[float],
    volumes: Sequence[float],
) -> list[float]:
    """
    Return the full On-Balance Volume series.

    The series starts at 0.0 and has the same length as the input.
    Returns an empty list if there are fewer than 2 bars.
    """
    _validate_series(closes, "closes")
    _validate_series(volumes, "volumes")
    if len(closes) != len(volumes):
        raise ValueError("closes and volumes must have equal length.")
    n = len(closes)
    if n < 2:
        return []
    result = [0.0]
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


# ---------------------------------------------------------------------------
# Trend structure
# ---------------------------------------------------------------------------


def detect_swings(
    closes: Sequence[float],
    lookback: int = 20,
) -> tuple[bool, bool] | None:
    """
    Detect higher highs and lower lows in the recent window.

    Returns ``(higher_highs, lower_lows)`` or ``None`` if there are
    fewer than ``lookback`` closes.

    A local high is a point higher than both neighbors; a local low is a
    point lower than both neighbors. ``higher_highs`` is True when the
    most recent local high exceeds the previous local high. ``lower_lows``
    is True when the most recent local low is below the previous local low.
    """
    _validate_period(lookback, "lookback")
    _validate_series(closes, "closes")
    n = len(closes)
    if n < lookback:
        return None
    window = list(closes[-lookback:])
    highs: list[float] = []
    lows: list[float] = []
    for i in range(1, len(window) - 1):
        if window[i] > window[i - 1] and window[i] > window[i + 1]:
            highs.append(window[i])
        if window[i] < window[i - 1] and window[i] < window[i + 1]:
            lows.append(window[i])
    higher_highs = len(highs) >= 2 and highs[-1] > highs[-2]
    lower_lows = len(lows) >= 2 and lows[-1] < lows[-2]
    return (higher_highs, lower_lows)
