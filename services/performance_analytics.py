"""Deterministic performance analytics for labeled non-live observations."""

from collections import defaultdict
from math import isfinite, sqrt
from statistics import mean, pstdev

from core.research.provenance import stable_json
from models.performance_analytics import AdvancedPerformanceReport, PerformanceGroup


SOURCES = {"FIXTURE", "REPLAY", "PUBLIC_OBSERVATION", "PAPER"}
OUTCOMES = {"WIN", "LOSS", "FLAT", "REJECTED", "NO_TRADE"}


class PerformanceAnalyticsService:
    def analyze(self, observations, *, starting_equity):
        observations = tuple(sorted(observations, key=lambda item: (item.observed_at, item.observation_id)))
        self._validate(observations, starting_equity)
        if not observations:
            return AdvancedPerformanceReport(
                sample_size=0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                total_return=None,
                annualized_return=None,
                win_rate=None,
                loss_rate=None,
                average_win=None,
                average_loss=None,
                expectancy=None,
                profit_factor=None,
                maximum_drawdown=None,
                recovery_factor=None,
                sharpe_style=None,
                sortino_style=None,
                average_exposure=None,
                turnover=0.0,
                fee_impact=0.0,
                slippage_impact=0.0,
                calibration_error=None,
                rejection_quality=None,
                no_trade_quality=None,
                by_symbol=(),
                by_regime=(),
                by_timeframe=(),
                by_specialist=(),
                by_source=(),
                assumptions=self._assumptions(),
                warnings=("Insufficient samples: no performance observations.",),
            )
        trades = tuple(item for item in observations if item.outcome in {"WIN", "LOSS", "FLAT"})
        winners = tuple(item.realized_pnl for item in trades if item.realized_pnl > 0)
        losers = tuple(item.realized_pnl for item in trades if item.realized_pnl < 0)
        realized = sum(item.realized_pnl for item in observations)
        unrealized = observations[-1].unrealized_pnl
        total_return = (observations[-1].equity - starting_equity) / starting_equity
        days = (observations[-1].observed_at - observations[0].observed_at).total_seconds() / 86400
        annualized = None
        if days >= 365 and observations[-1].equity > 0:
            annualized = (observations[-1].equity / starting_equity) ** (365 / days) - 1
        returns = tuple(item.realized_pnl / starting_equity for item in trades)
        sharpe = self._ratio(returns, returns)
        downside = tuple(min(value, 0.0) for value in returns)
        sortino = self._ratio(returns, downside)
        maximum_drawdown = self._drawdown(observations)
        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        recovery = None if maximum_drawdown == 0 else realized / maximum_drawdown
        warnings = []
        if len(trades) < 5:
            warnings.append("Insufficient trade samples for robust inference.")
        if annualized is None:
            warnings.append("Annualized return withheld: history is shorter than 365 days.")
        if sharpe is None:
            warnings.append("Sharpe-style metric unavailable because return variance is zero or samples are insufficient.")
        if sortino is None:
            warnings.append("Sortino-style metric unavailable because downside variance is zero or samples are insufficient.")
        return AdvancedPerformanceReport(
            len(observations), round(realized, 6), round(unrealized, 6),
            round(total_return, 6), self._round(annualized),
            self._rate(len(winners), len(trades)), self._rate(len(losers), len(trades)),
            self._mean(winners), self._mean(losers),
            self._mean(tuple(item.realized_pnl for item in trades)),
            None if gross_loss == 0 else round(gross_profit / gross_loss, 6),
            round(maximum_drawdown, 6), self._round(recovery), self._round(sharpe),
            self._round(sortino), round(mean(item.exposure for item in observations), 6),
            round(sum(item.turnover for item in observations), 6),
            round(sum(item.fees for item in observations), 6),
            round(sum(item.slippage for item in observations), 6),
            round(mean((item.confidence - float(item.correct)) ** 2 for item in observations), 6),
            self._quality(observations, "REJECTED"), self._quality(observations, "NO_TRADE"),
            self._groups(observations, "symbol"), self._groups(observations, "regime"),
            self._groups(observations, "timeframe"), self._groups(observations, "specialist"),
            self._groups(observations, "source"), self._assumptions(), tuple(warnings),
        )

    @staticmethod
    def serialize(report):
        if not isinstance(report, AdvancedPerformanceReport):
            raise ValueError("An advanced performance report is required.")
        return stable_json(report)

    @staticmethod
    def _validate(observations, starting_equity):
        if not isfinite(starting_equity) or starting_equity <= 0:
            raise ValueError("Starting equity must be finite and positive.")
        identifiers = set()
        for item in observations:
            values = (item.realized_pnl, item.unrealized_pnl, item.equity, item.exposure,
                      item.turnover, item.fees, item.slippage, item.confidence)
            if item.observation_id in identifiers or not item.observation_id.strip():
                raise ValueError("Performance observation identifiers must be unique.")
            identifiers.add(item.observation_id)
            if (
                item.observed_at.tzinfo is None
                or item.observed_at.utcoffset().total_seconds() != 0
                or any(not isfinite(value) for value in values)
            ):
                raise ValueError("Performance observations require UTC-aware finite values.")
            if item.source not in SOURCES or item.outcome not in OUTCOMES:
                raise ValueError("Performance source or outcome is invalid.")
            if not 0 <= item.confidence <= 1 or item.equity < 0 or item.exposure < 0:
                raise ValueError("Performance bounds are invalid.")

    @staticmethod
    def _drawdown(observations):
        peak = observations[0].equity
        result = 0.0
        for item in observations:
            peak = max(peak, item.equity)
            result = max(result, peak - item.equity)
        return result

    @staticmethod
    def _ratio(returns, dispersion_values):
        if len(returns) < 2:
            return None
        dispersion = pstdev(dispersion_values)
        return None if dispersion == 0 else mean(returns) / dispersion * sqrt(len(returns))

    @staticmethod
    def _groups(observations, field):
        grouped = defaultdict(list)
        for item in observations:
            grouped[getattr(item, field)].append(item)
        result = []
        for label, items in sorted(grouped.items()):
            trades = [item for item in items if item.outcome in {"WIN", "LOSS", "FLAT"}]
            wins = sum(1 for item in trades if item.realized_pnl > 0)
            result.append(PerformanceGroup(label, len(items), round(sum(item.realized_pnl for item in items), 6), PerformanceAnalyticsService._rate(wins, len(trades))))
        return tuple(result)

    @staticmethod
    def _quality(observations, outcome):
        selected = [item for item in observations if item.outcome == outcome]
        return None if not selected else round(mean(float(item.correct) for item in selected), 6)

    @staticmethod
    def _rate(numerator, denominator):
        return None if denominator == 0 else round(numerator / denominator, 6)

    @staticmethod
    def _mean(values):
        return None if not values else round(mean(values), 6)

    @staticmethod
    def _round(value):
        return None if value is None else round(value, 6)

    @staticmethod
    def _assumptions():
        return (
            "Sharpe-style and Sortino-style metrics use observed trade returns, a zero target, and no risk-free rate.",
            "Fixture, replay, public-observation, and paper results are separated and do not establish profitability.",
        )
