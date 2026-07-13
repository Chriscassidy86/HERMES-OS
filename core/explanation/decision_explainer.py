"""Deterministically translate decision artifacts into a human explanation."""

from datetime import datetime, timezone

from models.decision_explanation import DecisionExplanation


class DecisionExplainer:
    def explain(self, result) -> DecisionExplanation:
        if isinstance(result, dict):
            return self._from_mapping(result)
        return self._from_mapping({
            "cycle_id": result.cycle_id,
            "timestamp": result.timestamp,
            "snapshot": self._mapping(result.snapshot),
            "evidence_summary": self._mapping(result.evidence_summary),
            "recommendation": self._mapping(result.recommendation),
            "risk_assessment": self._mapping(result.risk_assessment),
            "rejection_reasons": result.rejection_reasons,
            "final_status": result.final_status,
        })

    def _from_mapping(self, value: dict) -> DecisionExplanation:
        evidence = value.get("evidence_summary") or {}
        recommendation = value.get("recommendation") or {}
        risk = value.get("risk_assessment") or {}
        snapshot = value.get("snapshot") or {}
        contributions = tuple(evidence.get("contributions") or ())
        action = recommendation.get("action", "WAIT")
        agreements = []
        disagreements = []
        ignored = []
        ignored_reasons = []
        why = []
        for contribution in contributions:
            source = contribution.get("source", "Unknown specialist")
            direction = contribution.get("direction", "WAIT")
            if contribution.get("included"):
                why.append(
                    f"{source} contributed {direction} evidence with weighted score "
                    f"{float(contribution.get('weighted_score', 0)):.4f}."
                )
                if direction == action:
                    agreements.append(source)
                elif direction in {"LONG", "SHORT"}:
                    disagreements.append(source)
            else:
                ignored.append(source)
                ignored_reasons.append(f"{source}: {contribution.get('reason', 'No reason supplied.')}")
        uncertainties = list(evidence.get("conflicting_evidence") or ())
        uncertainties.extend(evidence.get("excluded_evidence") or ())
        if float(recommendation.get("confidence", 0)) < 60:
            uncertainties.append("Recommendation confidence is below 60%.")
        rejection_reasons = tuple(value.get("rejection_reasons") or ())
        uncertainties.extend(rejection_reasons)
        if not uncertainties:
            uncertainties.append("Future market conditions and paper execution outcomes remain uncertain.")
        timestamp = value.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError("Decision explanation requires a timezone-aware decision timestamp.")
        trend = snapshot.get("market_trend", "unknown")
        status = value.get("final_status", "UNKNOWN")
        approved = bool(risk.get("approved", False))
        risk_reason = risk.get("reason", "No Risk Manager reason supplied.")
        return DecisionExplanation(
            value.get("cycle_id", "UNKNOWN"),
            action,
            float(recommendation.get("confidence", 0)),
            f"{snapshot.get('symbol', 'UNKNOWN')} is classified as {trend}; decision status is {status}.",
            tuple(why) or (recommendation.get("reason", "No recommendation reason supplied."),),
            tuple(sorted(set(agreements))),
            tuple(sorted(set(disagreements))),
            tuple(ignored),
            tuple(ignored_reasons),
            f"Risk Manager {'approved' if approved else 'rejected'} the recommendation: {risk_reason}",
            (
                "Market snapshot values are treated as supplied observations after validation.",
                "Configured deterministic weights and thresholds are assumed unchanged.",
                "Any execution eligibility applies to PAPER mode only.",
            ),
            tuple(dict.fromkeys(uncertainties)),
            timestamp.astimezone(timezone.utc),
        )

    @staticmethod
    def _mapping(value):
        from dataclasses import asdict
        return asdict(value)

