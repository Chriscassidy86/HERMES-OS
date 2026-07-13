"""Paper-only application service for the Hermes decision pipeline."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any

from agents.base.base_specialist import BaseSpecialist
from agents.market_regime.market_regime_specialist import MarketRegimeSpecialist
from agents.momentum.momentum_specialist import MomentumSpecialist
from agents.trend.trend_specialist import TrendSpecialist
from agents.volatility.volatility_specialist import VolatilitySpecialist
from agents.volume_agent.volume_specialist import VolumeSpecialist
from core.evidence.evidence_analyzer import EvidenceAnalyzer
from core.recommendation.recommendation_engine import RecommendationEngine
from core.risk.risk_manager import RiskManager
from models.cycle_result import DecisionCycleResult
from models.decision_packet import DecisionPacket
from models.recommendation import Recommendation
from models.signal import Signal
from reports.agent_report import AgentReport
from reports.market_snapshot import MarketSnapshot


class DecisionCycle:
    """Run one validated decision cycle without placing an order."""

    def __init__(
        self,
        specialists: Iterable[BaseSpecialist] | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._specialists = tuple(specialists) if specialists is not None else (
            TrendSpecialist(), MarketRegimeSpecialist(), MomentumSpecialist(),
            VolumeSpecialist(), VolatilitySpecialist(),
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._evidence = EvidenceAnalyzer()
        self._recommendations = RecommendationEngine()
        self._risk = RiskManager()

    def run(self, snapshot: MarketSnapshot) -> DecisionCycleResult:
        timestamp = self._normalized_timestamp(self._clock())
        rejection_reasons = self._validate_snapshot(snapshot)
        if (
            isinstance(snapshot, MarketSnapshot)
            and isinstance(snapshot.timestamp, datetime)
            and snapshot.timestamp.tzinfo is not None
            and snapshot.timestamp.astimezone(timezone.utc) > timestamp + timedelta(seconds=60)
        ):
            rejection_reasons.append("Snapshot timestamp is in the future.")
        symbol = (
            snapshot.symbol.strip()
            if isinstance(snapshot, MarketSnapshot)
            and isinstance(snapshot.symbol, str)
            and snapshot.symbol.strip()
            else "UNKNOWN"
        )
        cycle_id = f"{symbol.replace('/', '-')}-{timestamp:%Y%m%dT%H%M%SZ}"
        reports: list[AgentReport] = []
        signals: list[Signal] = []

        for specialist in self._specialists if not rejection_reasons else ():
            try:
                output: Any = specialist.analyze(snapshot)
            except Exception as exc:  # Fail closed at the specialist boundary.
                rejection_reasons.append(
                    f"{specialist.name}: analysis failed ({type(exc).__name__})"
                )
                continue

            validation_error = self._validate_specialist_output(specialist, output)
            if validation_error:
                rejection_reasons.append(validation_error)
                continue

            report, signal = output
            reports.append(replace(report, created_at=timestamp))
            signals.append(signal)

        if not signals:
            rejection_reasons.append("No valid specialist signals were produced.")

        packet = DecisionPacket(
            symbol=symbol,
            signals=tuple(signals),
            created_at=timestamp,
        )
        evidence_summary = self._evidence.analyze(packet, as_of=timestamp)
        if evidence_summary.conflicting_evidence:
            rejection_reasons.extend(
                f"Contradictory evidence: {reason}"
                for reason in evidence_summary.conflicting_evidence
            )
        invalid_exclusions = tuple(
            reason
            for reason in evidence_summary.excluded_evidence
            if any(
                marker in reason.lower()
                for marker in ("stale", "future", "incompatible", "no configured trust")
            )
        )
        if invalid_exclusions:
            rejection_reasons.extend(
                f"Excluded evidence: {reason}"
                for reason in invalid_exclusions
            )

        if rejection_reasons:
            recommendation = Recommendation(
                symbol=symbol,
                action="WAIT",
                confidence=0.0,
                reason="Decision cycle failed closed because evidence was invalid.",
            )
            final_status = "REJECTED_INVALID_EVIDENCE"
        else:
            recommendation = self._recommendations.recommend(evidence_summary)
            final_status = "EVALUATED"

        risk_assessment = self._risk.evaluate(recommendation)
        if not risk_assessment.approved:
            rejection_reasons.append(f"Risk rejected: {risk_assessment.reason}")

        eligible = (
            not rejection_reasons
            and risk_assessment.approved
            and recommendation.action in {"LONG", "SHORT"}
        )
        if eligible:
            final_status = "PAPER_EXECUTION_ELIGIBLE"
        elif final_status == "EVALUATED":
            final_status = "REJECTED_BY_RISK"

        return DecisionCycleResult(
            cycle_id=cycle_id,
            timestamp=timestamp,
            snapshot=snapshot,
            specialist_reports=tuple(reports),
            decision_packet=packet,
            evidence_summary=evidence_summary,
            recommendation=recommendation,
            risk_assessment=risk_assessment,
            final_status=final_status,
            rejection_reasons=tuple(rejection_reasons),
            paper_execution_eligible=eligible,
        )

    @staticmethod
    def _normalized_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("DecisionCycle clock must return a timezone-aware datetime.")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_snapshot(snapshot: MarketSnapshot) -> list[str]:
        errors: list[str] = []
        if not isinstance(snapshot, MarketSnapshot):
            return ["Snapshot must be a MarketSnapshot."]
        if not isinstance(snapshot.symbol, str) or not snapshot.symbol.strip():
            errors.append("Snapshot symbol is required.")
        if not DecisionCycle._is_number(snapshot.price) or snapshot.price <= 0:
            errors.append("Snapshot price must be finite and greater than zero.")
        if not DecisionCycle._is_number(snapshot.volume_24h) or snapshot.volume_24h < 0:
            errors.append("Snapshot volume must be finite and non-negative.")
        if not isinstance(snapshot.market_trend, str) or not snapshot.market_trend.strip():
            errors.append("Snapshot market trend is required.")
        if not DecisionCycle._is_number(snapshot.volatility) or snapshot.volatility < 0:
            errors.append("Snapshot volatility must be finite and non-negative.")
        if (
            not DecisionCycle._is_number(snapshot.fear_greed_index)
            or not 0 <= snapshot.fear_greed_index <= 100
        ):
            errors.append("Fear and greed index must be between 0 and 100.")
        for name, value in (
            ("previous price", snapshot.previous_price),
            ("average volume", snapshot.average_volume),
            ("short moving average", snapshot.short_moving_average),
            ("long moving average", snapshot.long_moving_average),
        ):
            if value is not None and (not DecisionCycle._is_number(value) or value <= 0):
                errors.append(f"Snapshot {name} must be finite and greater than zero.")
        if not isinstance(snapshot.timeframe, str) or not snapshot.timeframe.strip():
            errors.append("Snapshot timeframe is required.")
        if not isinstance(snapshot.timestamp, datetime) or snapshot.timestamp.tzinfo is None:
            errors.append("Snapshot timestamp must be timezone-aware.")
        return errors

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)

    @staticmethod
    def _validate_specialist_output(
        specialist: BaseSpecialist, output: Any
    ) -> str | None:
        if not isinstance(output, tuple) or len(output) != 2:
            return f"{specialist.name}: expected an (AgentReport, Signal) tuple."
        report, signal = output
        if not isinstance(report, AgentReport) or not report.is_valid():
            return f"{specialist.name}: malformed AgentReport."
        if not isinstance(signal, Signal):
            return f"{specialist.name}: malformed Signal."
        if not isinstance(signal.timestamp, datetime) or signal.timestamp.tzinfo is None:
            return f"{specialist.name}: signal timestamp is invalid."
        if not signal.evidence:
            return f"{specialist.name}: signal evidence is missing."
        if report.agent_name != specialist.name or signal.source != specialist.name:
            return f"{specialist.name}: report or signal source mismatch."
        if signal.direction not in {"LONG", "SHORT", "WAIT"}:
            return f"{specialist.name}: invalid signal direction."
        if not DecisionCycle._is_number(signal.confidence) or not 0 <= signal.confidence <= 100:
            return f"{specialist.name}: signal confidence is out of range."
        if not DecisionCycle._is_number(signal.strength) or not 0 <= signal.strength <= 1:
            return f"{specialist.name}: signal strength is out of range."
        if (
            not isinstance(signal.timeframe, str)
            or not signal.timeframe.strip()
            or not isinstance(signal.priority, int)
            or isinstance(signal.priority, bool)
            or signal.priority < 1
        ):
            return f"{specialist.name}: signal timeframe or priority is invalid."
        return None
