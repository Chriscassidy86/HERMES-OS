"""Offline deterministic research orchestration and reproducibility services."""

from dataclasses import replace
from datetime import datetime, timezone
from math import isfinite
from platform import python_version
from statistics import mean

from core.research.provenance import DatasetCatalog, stable_checksum, stable_json
from database.research_repository import DuplicateResearchRunError
from models.research_provenance import (
    CalibrationAdoptionProposal,
    CalibrationObservation,
    ReproducibilityExport,
    ResearchComparison,
    ResearchConfiguration,
    ResearchMetricSet,
    ResearchRunManifest,
    ResearchRunResult,
    RollingCalibrationReport,
    WalkForwardSplit,
    ProvenanceDifference,
)


class ResearchRunOrchestrator:
    def __init__(self, repository, *, clock=None):
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, *, run_id, code_commit, dataset_rows, configurations,
            reproducibility_seed, strategy_versions, specialist_versions,
            environment_summary=(), human_approval_state="NOT_REQUIRED_FOR_OFFLINE_RESEARCH"):
        if self.repository.load_run(run_id) is not None: raise DuplicateResearchRunError(run_id)
        started = self._now()
        if not dataset_rows or not configurations: raise ValueError("Datasets and configurations are required.")
        records = []
        symbols = set(); timeframes = set()
        for dataset_id, rows in sorted(dataset_rows.items()):
            payload = self.repository.load_dataset(dataset_id)
            if payload is None: raise ValueError(f"Research dataset is missing: {dataset_id}.")
            record = self._record(payload)
            DatasetCatalog.verify(record, tuple(rows))
            if record.label not in {"FIXTURE", "REPLAY", "PUBLIC_OBSERVATION", "PAPER"}:
                raise ValueError("Research dataset boundary is invalid.")
            records.append(record); symbols.add(record.symbol); timeframes.add(record.timeframe)
        metrics = tuple(self._metrics(config, dataset_rows) for config in configurations)
        artifact_ids = tuple(f"{run_id}:metrics:{item.label}" for item in metrics)
        fingerprint = stable_checksum(tuple(configurations))
        ended = self._now()
        manifest = ResearchRunManifest(
            run_id, code_commit, fingerprint, tuple(sorted(dataset_rows)),
            int(reproducibility_seed), started, ended, tuple(sorted(symbols)),
            tuple(sorted(timeframes)), tuple(sorted(strategy_versions)),
            tuple(sorted(specialist_versions)), artifact_ids,
            tuple(sorted(environment_summary)) + (("python", python_version()),),
            "PAPER", human_approval_state,
        )
        for artifact_id, metric in zip(artifact_ids, metrics):
            self.repository.save_artifact(artifact_id, "RESEARCH_METRICS", metric, ended)
        self.repository.save_run(manifest)
        return ResearchRunResult(
            manifest, metrics, tuple((record.dataset_id, record.checksum) for record in records)
        )

    @staticmethod
    def _record(payload):
        from datetime import datetime
        from models.research_provenance import DatasetRecord
        value = dict(payload)
        for key in ("start_time", "end_time", "ingested_at"): value[key] = datetime.fromisoformat(value[key])
        value["reliability_notes"] = tuple(value["reliability_notes"])
        return DatasetRecord(**value)

    @staticmethod
    def _metrics(config: ResearchConfiguration, dataset_rows):
        if not isinstance(config, ResearchConfiguration) or not config.label.strip() or not config.fingerprint.strip():
            raise ValueError("Research configurations must be immutable and identified.")
        if not isfinite(config.signal_threshold) or config.signal_threshold < 0:
            raise ValueError("Research signal threshold is invalid.")
        returns = []; calibration = []; correct = []
        for _, rows in sorted(dataset_rows.items()):
            rows = tuple(rows)
            closes = [float(item["close"]) for item in rows]
            if len(closes) < 2 or any(not isfinite(value) or value <= 0 for value in closes):
                raise ValueError("Research rows require at least two finite positive closes.")
            for previous, current, row in zip(closes, closes[1:], rows[1:]):
                change = (current - previous) / previous
                returns.append(change if abs(change) >= config.signal_threshold else 0.0)
                if "confidence" in row and "prediction" in row:
                    confidence = float(row["confidence"])
                    if not 0 <= confidence <= 1: raise ValueError("Research confidence must be between zero and one.")
                    actual = "LONG" if current > previous else ("SHORT" if current < previous else "WAIT")
                    observed = 1.0 if row["prediction"] == actual else 0.0
                    calibration.append((confidence - observed) ** 2); correct.append(observed)
        equity = peak = 1.0; drawdown = 0.0
        for value in returns:
            equity *= 1 + value; peak = max(peak, equity); drawdown = max(drawdown, peak - equity)
        return ResearchMetricSet(
            config.label, round(equity - 1, 6), round(drawdown, 6),
            round(mean(calibration), 6) if calibration else 0.0,
            round(mean(correct), 6) if correct else 0.0,
        )

    def _now(self):
        value = self.clock()
        if value.tzinfo is None: raise ValueError("Research clock must be timezone-aware.")
        return value.astimezone(timezone.utc)


class WalkForwardEvaluator:
    def split(self, rows, *, split_id, training_size, validation_size, test_size,
              artificial_fixture):
        rows = tuple(rows); required = training_size + validation_size + test_size
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
               for value in (training_size, validation_size, test_size)):
            raise ValueError("Walk-forward window sizes must be positive integers.")
        if len(rows) < required: raise ValueError("Insufficient history for walk-forward evaluation.")
        selected = rows[:required]
        timestamps = [self._timestamp(item) for item in selected]
        if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
            raise ValueError("Walk-forward rows must be strictly ordered and unique.")
        identifiers = tuple(str(item.get("id", index)) for index, item in enumerate(selected))
        train_end = training_size; validation_end = train_end + validation_size
        if not timestamps[train_end - 1] < timestamps[train_end] < timestamps[validation_end]:
            raise ValueError("Walk-forward windows violate no-look-ahead separation.")
        return WalkForwardSplit(
            split_id, identifiers[:train_end], identifiers[train_end:validation_end],
            identifiers[validation_end:], bool(artificial_fixture), True
        )

    @staticmethod
    def _timestamp(row):
        value = row.get("timestamp")
        if isinstance(value, str): value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Walk-forward rows require timezone-aware timestamps.")
        return value.astimezone(timezone.utc)


class ResearchComparisonService:
    def compare(self, baseline: ResearchMetricSet, candidate: ResearchMetricSet, *,
                baseline_manifest=None, candidate_manifest=None):
        if not isinstance(baseline, ResearchMetricSet) or not isinstance(candidate, ResearchMetricSet):
            raise ValueError("Baseline and candidate research metrics are required.")
        reproducible = False
        if baseline_manifest is not None and candidate_manifest is not None:
            reproducible = (
                baseline_manifest.code_commit == candidate_manifest.code_commit
                and baseline_manifest.dataset_ids == candidate_manifest.dataset_ids
                and baseline_manifest.reproducibility_seed == candidate_manifest.reproducibility_seed
            )
        return ResearchComparison(
            baseline.label, candidate.label,
            round(candidate.total_return - baseline.total_return, 6),
            round(candidate.maximum_drawdown - baseline.maximum_drawdown, 6),
            round(candidate.calibration_score - baseline.calibration_score, 6),
            round(candidate.specialist_accuracy - baseline.specialist_accuracy, 6),
            reproducible,
            ("Metric deltas may reflect sampling noise or regime dependence.",),
            ("Artificial, replay, public-observation, and paper results do not prove profitability.",),
        )

    @staticmethod
    def compare_runs(baseline: ResearchRunResult, candidate: ResearchRunResult):
        differences=[]
        if baseline.manifest.code_commit!=candidate.manifest.code_commit: differences.append("Code commit differs.")
        if baseline.manifest.configuration_fingerprint!=candidate.manifest.configuration_fingerprint: differences.append("Configuration fingerprint differs.")
        if baseline.manifest.dataset_ids!=candidate.manifest.dataset_ids: differences.append("Dataset identifiers differ.")
        if baseline.manifest.reproducibility_seed!=candidate.manifest.reproducibility_seed: differences.append("Reproducibility seed differs.")
        return ProvenanceDifference("RUN",baseline.manifest.run_id,candidate.manifest.run_id,tuple(differences),not differences)

    @staticmethod
    def compare_datasets(baseline, candidate):
        differences=[]
        for field,label in (("checksum","Checksum"),("schema_version","Schema version"),("symbol","Symbol"),("timeframe","Timeframe"),("row_count","Row count"),("label","Dataset label")):
            if getattr(baseline,field)!=getattr(candidate,field): differences.append(f"{label} differs.")
        return ProvenanceDifference("DATASET",baseline.dataset_id,candidate.dataset_id,tuple(differences),not differences)

    @staticmethod
    def compare_configurations(baseline: ResearchConfiguration, candidate: ResearchConfiguration):
        differences=[]
        if baseline.fingerprint!=candidate.fingerprint: differences.append("Configuration fingerprint differs.")
        if baseline.signal_threshold!=candidate.signal_threshold: differences.append("Signal threshold differs.")
        return ProvenanceDifference("CONFIGURATION",baseline.label,candidate.label,tuple(differences),not differences)


class ReproducibilityExporter:
    def export(self, manifest: ResearchRunManifest, dependencies=()):
        if manifest.mode != "PAPER": raise ValueError("Only PAPER research manifests may be exported.")
        payload = {"manifest": manifest, "dependencies": tuple(sorted(dependencies))}
        manifest_json = stable_json(payload)
        return ReproducibilityExport(
            manifest_json, stable_checksum(payload),
            f"python examples/research_job_demo.py --run-id {manifest.run_id}",
            tuple(sorted(dependencies)),
        )

    @staticmethod
    def verify(value: ReproducibilityExport):
        import json
        payload = json.loads(value.manifest_json)
        if stable_checksum(payload) != value.checksum:
            raise ValueError("Reproducibility export checksum verification failed.")
        return True


class CalibrationMonitor:
    def report(self, observations: tuple[CalibrationObservation, ...], *, min_samples=10,
               window_size=50):
        if min_samples < 2 or window_size < min_samples: raise ValueError("Calibration sample gates are invalid.")
        if len(observations) < min_samples: raise ValueError("Insufficient samples for calibration monitoring.")
        window = tuple(sorted(observations, key=lambda item: item.observed_at))[-window_size:]
        for item in window:
            if (not item.observation_id.strip() or item.observed_at.tzinfo is None
                    or not isfinite(item.confidence) or not 0 <= item.confidence <= 1):
                raise ValueError("Calibration observation is malformed.")
        confidence = mean(item.confidence for item in window)
        accuracy = mean(1.0 if item.correct else 0.0 for item in window)
        brier = mean((item.confidence - (1.0 if item.correct else 0.0)) ** 2 for item in window)
        gap = confidence - accuracy
        status = "OVERCONFIDENT" if gap >= 0.15 else ("UNDERCONFIDENT" if gap <= -0.15 else "CALIBRATED")
        proposal = CalibrationAdoptionProposal(
            status,
            f"Mean confidence {confidence:.4f}; observed accuracy {accuracy:.4f}; Brier score {brier:.4f}.",
            len(window), True, False,
        )
        return RollingCalibrationReport(
            len(window), round(brier, 6), round(confidence, 6), round(accuracy, 6),
            status, proposal, window[0].observed_at.astimezone(timezone.utc),
            window[-1].observed_at.astimezone(timezone.utc),
        )
