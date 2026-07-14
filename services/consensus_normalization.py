"""Transparent deterministic normalization without executable semantics."""

from collections import defaultdict
from datetime import datetime, timezone

from models.consensus_normalization import ConsensusNormalization
from models.market_consensus import ConsensusConflict, ConsensusContribution, ConsensusDirection, SourceCategory, utc


class ConsensusNormalizationEngine:
    CATEGORY_CAP = 0.45
    MIN_INDEPENDENT_SOURCES = 2
    MAX_AGE = {
        SourceCategory.TECHNICAL_CONSENSUS: 1800,
        SourceCategory.DERIVATIVES: 1800,
        SourceCategory.SENTIMENT: 172800,
        SourceCategory.ON_CHAIN: 7200,
        SourceCategory.MARKET_BREADTH: 3600,
        SourceCategory.NEWS: 3600,
        SourceCategory.ANALYST_COMMUNITY: 3600,
        SourceCategory.MACRO: 172800,
        SourceCategory.PUBLIC_EXCHANGE_METRICS: 18000,
    }

    def normalize(self, observations, *, symbol: str, timeframe: str, evaluated_at: datetime) -> ConsensusNormalization:
        now = utc(evaluated_at, "evaluated_at")
        values = tuple(sorted(tuple(observations), key=lambda item: (item.source_id, item.observed_at, item.observation_id)))
        excluded = []
        candidates = []
        for item in values:
            reason = self._exclusion(item, symbol, timeframe, now)
            if reason:
                excluded.append((item.observation_id, reason))
            else:
                candidates.append(item)

        seen_sources = set()
        seen_datasets = set()
        category_used = defaultdict(float)
        contributions = []
        freshness_reduced = False
        for item in candidates:
            max_age = self.MAX_AGE[item.source_category]
            age = max(0.0, (now - item.observed_at.astimezone(timezone.utc)).total_seconds())
            freshness = max(0.1, 1 - age / max_age)
            freshness_reduced = freshness_reduced or freshness < 0.5
            specificity = 1.0 if item.symbol == symbol else 0.45
            independent = item.source_id not in seen_sources and item.underlying_dataset not in seen_datasets
            independence = 1.0 if independent else 0.2
            base = item.signal.confidence * max(0.1, item.signal.strength) * item.source_reliability * freshness * specificity * independence
            remaining = max(0.0, self.CATEGORY_CAP - category_used[item.source_category])
            weight = round(min(base, remaining), 6)
            if item.source_id in seen_sources:
                explanation = "Repeated source contribution capped to prevent source amplification."
            elif item.underlying_dataset in seen_datasets:
                explanation = "Shared underlying dataset discounted and not counted as independent confirmation."
            elif specificity < 1:
                explanation = "Broad-market evidence discounted for symbol-specific consensus."
            else:
                explanation = "Fresh symbol-specific evidence adjusted by confidence, strength, and source reliability."
            adjusted = round(item.signal.score * specificity * independence, 6)
            contributions.append(ConsensusContribution(item.observation_id, item.source_id, item.source_category, item.signal.direction, item.signal.score, adjusted, weight, independent, explanation))
            category_used[item.source_category] += weight
            seen_sources.add(item.source_id)
            seen_datasets.add(item.underlying_dataset)

        positive = tuple(item for item in contributions if item.adjusted_score > 0.1 and item.weight > 0)
        negative = tuple(item for item in contributions if item.adjusted_score < -0.1 and item.weight > 0)
        neutral = tuple(item for item in contributions if -0.1 <= item.adjusted_score <= 0.1 or item.weight == 0)
        total_weight = sum(item.weight for item in contributions)
        score = round(sum(item.adjusted_score * item.weight for item in contributions) / total_weight, 6) if total_weight else 0.0
        independent_count = sum(item.independent and item.weight > 0 for item in contributions)
        categories = {item.category for item in contributions if item.weight > 0}
        conflict_strength = 0.0
        conflicts = ()
        if positive and negative:
            positive_strength = sum(item.weight for item in positive)
            negative_strength = sum(item.weight for item in negative)
            conflict_strength = min(1.0, min(positive_strength, negative_strength) / max(positive_strength, negative_strength))
            conflicts = (ConsensusConflict(tuple(sorted({item.source_id for item in positive + negative})), round(conflict_strength, 6), "Bullish and bearish eligible evidence conflict."),)
        diversity = min(1.0, independent_count / 3) * min(1.0, len(categories) / 2)
        confidence = min(1.0, total_weight / 1.2) * diversity * (1 - conflict_strength * 0.5)
        if independent_count < self.MIN_INDEPENDENT_SOURCES:
            confidence = 0.0
            direction = ConsensusDirection.UNKNOWN
        else:
            direction = self._direction(score)
        uncertainty = min(1.0, 1 - confidence + conflict_strength * 0.25)
        directional = len(positive) + len(negative)
        dominant = max(len(positive), len(negative)) / directional if directional else 0
        crowding = "Directional evidence is highly one-sided; contrarian crowding risk requires review." if directional >= 3 and dominant >= 0.8 else None
        category_total = sum(category_used.values())
        concentration = max(category_used.values(), default=0) / category_total if category_total else 0
        concentration_warning = "Consensus evidence is concentrated in one category or correlated dataset." if concentration > 0.6 or independent_count < len({item.source_id for item in contributions}) else None
        freshness_warning = "One or more included observations received substantial freshness decay." if freshness_reduced else None
        limitations = ["Normalization is advisory and cannot create BUY/SELL decisions or bypass Risk Manager."]
        if independent_count < self.MIN_INDEPENDENT_SOURCES:
            limitations.append("Insufficient independent evidence for directional consensus.")
        return ConsensusNormalization(symbol, timeframe, now, direction, score, round(confidence, 6), round(uncertainty, 6), len({item.source_id for item in contributions}), independent_count, len(categories), tuple(contributions), tuple(item.observation_id for item in positive), tuple(item.observation_id for item in negative), tuple(item.observation_id for item in neutral), tuple(sorted(excluded)), conflicts, crowding, concentration_warning, freshness_warning, tuple(limitations))

    def _exclusion(self, item, symbol, timeframe, now):
        if item.timeframe != timeframe:
            return "TIMEFRAME_MISMATCH"
        if item.symbol not in {symbol, "MARKET-WIDE"}:
            return "SYMBOL_MISMATCH"
        if item.observed_at.astimezone(timezone.utc) > now:
            return "FUTURE_OBSERVATION"
        if not item.eligible_for_consensus:
            return item.exclusion_reason or "INELIGIBLE"
        if (now - item.observed_at.astimezone(timezone.utc)).total_seconds() > self.MAX_AGE[item.source_category]:
            return "STALE_OBSERVATION"
        if item.signal.direction is ConsensusDirection.UNKNOWN:
            return "UNKNOWN_DIRECTION"
        return None

    @staticmethod
    def _direction(score):
        if score <= -0.75:
            return ConsensusDirection.STRONG_BEARISH
        if score <= -0.4:
            return ConsensusDirection.BEARISH
        if score < -0.1:
            return ConsensusDirection.LEAN_BEARISH
        if score < 0.1:
            return ConsensusDirection.NEUTRAL
        if score < 0.4:
            return ConsensusDirection.LEAN_BULLISH
        if score < 0.75:
            return ConsensusDirection.BULLISH
        return ConsensusDirection.STRONG_BULLISH
