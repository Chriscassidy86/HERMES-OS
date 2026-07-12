"""Deterministic, explainable weighted evidence aggregation."""

from datetime import datetime, timezone

from core.evidence.config import DEFAULT_EVIDENCE_CONFIG, EvidenceConfig
from models.decision_packet import DecisionPacket
from models.evidence_summary import EvidenceContribution, EvidenceSummary


class EvidenceAnalyzer:
    def __init__(self, config: EvidenceConfig = DEFAULT_EVIDENCE_CONFIG) -> None:
        self.config = config

    def analyze(
        self, packet: DecisionPacket, *, as_of: datetime | None = None
    ) -> EvidenceSummary:
        now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
        contributions: list[EvidenceContribution] = []
        excluded: list[str] = []
        bullish = bearish = neutral = 0
        signed_total = directional_weight = 0.0

        for signal in packet.signals:
            reason = "Included in weighted evidence."
            included = True
            age = (now - signal.timestamp.astimezone(timezone.utc)).total_seconds()
            freshness = max(0.0, 1.0 - max(age, 0.0) / self.config.max_age_seconds)
            timeframe = self.config.timeframe_compatibility.get(signal.timeframe, 0.0)
            weight = self.config.specialist_weights.get(signal.source, 0.0)
            reliability = self.config.source_reliability.get(signal.source, 0.0)

            if age < -self.config.max_future_skew_seconds:
                included, reason = False, "Signal timestamp is in the future."
            elif age > self.config.max_age_seconds:
                included, reason = False, "Signal is stale."
            elif signal.confidence < self.config.minimum_confidence:
                included, reason = False, "Signal confidence is below the configured minimum."
            elif timeframe == 0:
                included, reason = False, "Signal timeframe is incompatible."
            elif weight <= 0 or reliability <= 0:
                included, reason = False, "Signal source has no configured trust weight."

            base = weight * reliability * timeframe * freshness * signal.strength
            score = base * (signal.confidence / 100.0)
            if included and signal.direction == "LONG":
                bullish += 1
                signed_total += score
                directional_weight += base
            elif included and signal.direction == "SHORT":
                bearish += 1
                signed_total -= score
                directional_weight += base
            elif included:
                neutral += 1
                score = 0.0
                reason = "Neutral evidence recorded but excluded from directional confidence."
            else:
                score = 0.0
                excluded.append(f"{signal.source}: {reason}")

            contributions.append(EvidenceContribution(
                source=signal.source, direction=signal.direction,
                configured_weight=weight, confidence=signal.confidence,
                strength=signal.strength, freshness_factor=round(freshness, 4),
                timeframe_factor=timeframe, reliability=reliability,
                weighted_score=round(score, 6), included=included, reason=reason,
            ))

        directional_score = signed_total / directional_weight if directional_weight else 0.0
        conflicts = ()
        if bullish and bearish:
            conflicts = (f"Conflicting directional evidence: {bullish} bullish, {bearish} bearish.",)
        confidence = round(abs(directional_score) * 100, 2)
        return EvidenceSummary(
            symbol=packet.symbol, bullish=bullish, bearish=bearish, neutral=neutral,
            average_confidence=confidence, signal_count=packet.signal_count(),
            directional_score=round(directional_score, 6), final_confidence=confidence,
            contributions=tuple(contributions), conflicting_evidence=conflicts,
            excluded_evidence=tuple(excluded),
        )
