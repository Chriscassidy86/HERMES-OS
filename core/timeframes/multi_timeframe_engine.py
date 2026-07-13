"""Deterministic aggregation of specialist signals across five timeframes."""

from datetime import datetime, timedelta, timezone
from statistics import mean

from models.multi_timeframe import (
    HorizonExplanation,
    MultiTimeframeSummary,
    SpecialistTimeframeExplanation,
    TimeframeView,
)
from models.signal import Signal


SUPPORTED = ("5m", "15m", "1h", "4h", "Daily")
ALIASES = {"5M":"5m", "15M":"15m", "1H":"1h", "4H":"4h", "1D":"Daily", "DAILY":"Daily"}
HORIZONS = (("SHORT_TERM", ("5m", "15m")), ("MEDIUM_TERM", ("1h", "4h")), ("LONG_TERM", ("Daily",)))


class MultiTimeframeEngine:
    def analyze(self, symbol: str, signals: tuple[Signal, ...], *, as_of: datetime) -> MultiTimeframeSummary:
        if not symbol.strip() or not isinstance(as_of, datetime) or as_of.tzinfo is None:
            raise ValueError("Symbol and timezone-aware analysis time are required.")
        if not signals:
            raise ValueError("Multi-timeframe analysis requires specialist signals.")
        now = as_of.astimezone(timezone.utc)
        grouped: dict[str, dict[str, TimeframeView]] = {}
        for signal in signals:
            timeframe = ALIASES.get(signal.timeframe.upper())
            self._validate_signal(signal, timeframe, now)
            by_timeframe = grouped.setdefault(signal.source, {})
            if timeframe in by_timeframe:
                raise ValueError(f"Duplicate {timeframe} signal for {signal.source}.")
            by_timeframe[timeframe] = TimeframeView(
                timeframe, signal.direction, signal.confidence, signal.evidence,
                signal.timestamp.astimezone(timezone.utc)
            )
        explanations = []
        for source, values in sorted(grouped.items()):
            missing = tuple(item for item in SUPPORTED if item not in values)
            if missing:
                raise ValueError(f"{source} is missing required timeframes: {', '.join(missing)}.")
            horizons = tuple(self._horizon(label, frames, values) for label, frames in HORIZONS)
            directional = {item.direction for item in horizons if item.direction in {"LONG", "SHORT"}}
            conflicts = tuple(
                f"{item.horizon} contains conflicting timeframe directions."
                for item in horizons if item.direction == "CONFLICT"
            )
            if len(directional) > 1:
                conflicts += ("Short-, medium-, and long-term directions disagree.",)
            aligned = directional.pop() if len(directional) == 1 and not conflicts and all(
                item.direction in directional | {"LONG", "SHORT"} for item in horizons
            ) else "WAIT"
            explanations.append(SpecialistTimeframeExplanation(
                source, horizons[0], horizons[1], horizons[2], aligned, conflicts
            ))
        specialist_directions = {item.aligned_direction for item in explanations}
        conflicts = tuple(reason for item in explanations for reason in item.conflicts)
        if len(specialist_directions) == 1 and specialist_directions <= {"LONG", "SHORT"} and not conflicts:
            aligned = next(iter(specialist_directions))
        else:
            aligned = "WAIT"
            if len(specialist_directions - {"WAIT"}) > 1:
                conflicts += ("Specialists disagree on aligned timeframe direction.",)
        confidence = mean(
            horizon.confidence for item in explanations
            for horizon in (item.short_term, item.medium_term, item.long_term)
        )
        alignment = tuple(
            f"{item.source}: {item.aligned_direction} across short, medium, and long horizons."
            for item in explanations if item.aligned_direction != "WAIT"
        )
        return MultiTimeframeSummary(
            symbol.strip().upper(), tuple(explanations), aligned, round(confidence, 2),
            alignment, tuple(dict.fromkeys(conflicts)),
            ("All five required timeframes use validated supplied specialist signals.",
             "Multi-timeframe output remains subject to Risk Manager review."), now
        )

    @staticmethod
    def _horizon(label, timeframes, values):
        selected = tuple(values[item] for item in timeframes)
        directions = {item.direction for item in selected if item.direction in {"LONG", "SHORT"}}
        if len(directions) > 1:
            direction = "CONFLICT"
        elif len(directions) == 1 and all(item.direction != "WAIT" for item in selected):
            direction = next(iter(directions))
        else:
            direction = "WAIT"
        uncertainty = () if direction in {"LONG", "SHORT"} else (
            f"{label} lacks complete directional alignment.",
        )
        return HorizonExplanation(
            label, direction, round(mean(item.confidence for item in selected), 2),
            tuple(timeframes), tuple(text for item in selected for text in item.evidence), uncertainty
        )

    @staticmethod
    def _validate_signal(signal, timeframe, now):
        if not isinstance(signal, Signal) or timeframe not in SUPPORTED:
            raise ValueError("Only supported 5m, 15m, 1h, 4h, and Daily signals are accepted.")
        if signal.direction not in {"LONG", "SHORT", "WAIT"} or not 0 <= signal.confidence <= 100:
            raise ValueError("Multi-timeframe signal direction or confidence is invalid.")
        if not signal.evidence or signal.timestamp.tzinfo is None:
            raise ValueError("Multi-timeframe signals require evidence and timezone-aware timestamps.")
        age = now - signal.timestamp.astimezone(timezone.utc)
        if age < -timedelta(seconds=60) or age > timedelta(days=2):
            raise ValueError("Multi-timeframe signal is future-dated or stale.")

