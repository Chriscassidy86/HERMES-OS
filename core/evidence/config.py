"""Explicit configuration for deterministic weighted evidence."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceConfig:
    specialist_weights: dict[str, float] = field(default_factory=lambda: {
        "Trend Specialist": 1.0,
        "Market Regime Specialist": 1.0,
        "Momentum Specialist": 0.9,
        "Volume Specialist": 0.8,
        "Volatility Specialist": 0.7,
    })
    source_reliability: dict[str, float] = field(default_factory=lambda: {
        "Trend Specialist": 1.0,
        "Market Regime Specialist": 1.0,
        "Momentum Specialist": 0.95,
        "Volume Specialist": 0.9,
        "Volatility Specialist": 0.9,
    })
    timeframe_compatibility: dict[str, float] = field(default_factory=lambda: {
        "4H": 1.0, "1H": 0.75,
    })
    target_timeframe: str = "4H"
    minimum_confidence: float = 50.0
    max_age_seconds: int = 14_400
    max_future_skew_seconds: int = 60


DEFAULT_EVIDENCE_CONFIG = EvidenceConfig()
