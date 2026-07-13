"""Immutable V3.6 research provenance, evaluation, and calibration records."""

from dataclasses import dataclass
from datetime import datetime


DATASET_LABELS = ("FIXTURE", "REPLAY", "PUBLIC_OBSERVATION", "PAPER")


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    source: str
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    row_count: int
    checksum: str
    trust_score: float
    reliability_notes: tuple[str, ...]
    ingested_at: datetime
    schema_version: int
    label: str


@dataclass(frozen=True)
class ResearchConfiguration:
    label: str
    fingerprint: str
    signal_threshold: float


@dataclass(frozen=True)
class ResearchMetricSet:
    label: str
    total_return: float
    maximum_drawdown: float
    calibration_score: float
    specialist_accuracy: float


@dataclass(frozen=True)
class ResearchRunManifest:
    run_id: str
    code_commit: str
    configuration_fingerprint: str
    dataset_ids: tuple[str, ...]
    reproducibility_seed: int
    started_at: datetime
    ended_at: datetime
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    strategy_versions: tuple[tuple[str, str], ...]
    specialist_versions: tuple[tuple[str, str], ...]
    result_artifact_ids: tuple[str, ...]
    environment_summary: tuple[tuple[str, str], ...]
    mode: str
    human_approval_state: str
    schema_version: int = 1


@dataclass(frozen=True)
class ResearchRunResult:
    manifest: ResearchRunManifest
    metrics: tuple[ResearchMetricSet, ...]
    dataset_checksums: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class WalkForwardSplit:
    split_id: str
    training_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    artificial_fixture: bool
    no_lookahead_enforced: bool = True


@dataclass(frozen=True)
class ResearchComparison:
    baseline_label: str
    candidate_label: str
    total_return_delta: float
    drawdown_delta: float
    calibration_delta: float
    specialist_accuracy_delta: float
    reproducibility_confirmed: bool
    uncertainty: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ProvenanceDifference:
    category: str
    baseline_id: str
    candidate_id: str
    differences: tuple[str, ...]
    identical: bool


@dataclass(frozen=True)
class CalibrationObservation:
    observation_id: str
    confidence: float
    correct: bool
    observed_at: datetime


@dataclass(frozen=True)
class CalibrationAdoptionProposal:
    finding: str
    evidence: str
    sample_size: int
    human_approval_required: bool = True
    configuration_modified: bool = False


@dataclass(frozen=True)
class RollingCalibrationReport:
    sample_size: int
    brier_score: float
    mean_confidence: float
    observed_accuracy: float
    status: str
    proposal: CalibrationAdoptionProposal
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True)
class ReproducibilityExport:
    manifest_json: str
    checksum: str
    rerun_command: str
    dependencies: tuple[tuple[str, str], ...]
