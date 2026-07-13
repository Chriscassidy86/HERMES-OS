"""Stable research serialization, checksums, and dataset catalog validation."""

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from math import isfinite

from models.research_provenance import DATASET_LABELS, DatasetRecord


def _normalize(value):
    if is_dataclass(value): return _normalize(asdict(value))
    if isinstance(value, dict): return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)): return [_normalize(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError("Research timestamps must be timezone-aware.")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, Enum): return value.value
    if isinstance(value, float) and not isfinite(value): raise ValueError("Research values must be finite.")
    return value


def stable_json(value) -> str:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_checksum(value) -> str:
    return sha256(stable_json(value).encode("utf-8")).hexdigest()


class DatasetCatalog:
    def __init__(self, repository=None): self.repository = repository

    def catalog(self, *, dataset_id, source, symbol, timeframe, start_time, end_time,
                rows, trust_score, reliability_notes, ingested_at, label,
                schema_version=1):
        rows = tuple(rows)
        self._validate(dataset_id, source, symbol, timeframe, start_time, end_time,
                       rows, trust_score, ingested_at, label, schema_version)
        record = DatasetRecord(
            dataset_id, source, symbol.upper(), timeframe, start_time.astimezone(timezone.utc),
            end_time.astimezone(timezone.utc), len(rows), stable_checksum(rows), trust_score,
            tuple(reliability_notes), ingested_at.astimezone(timezone.utc), schema_version, label
        )
        if self.repository is not None: self.repository.save_dataset(record)
        return record

    @staticmethod
    def verify(record: DatasetRecord, rows) -> bool:
        if not isinstance(record, DatasetRecord): raise ValueError("A dataset record is required.")
        rows = tuple(rows)
        if len(rows) != record.row_count or stable_checksum(rows) != record.checksum:
            raise ValueError("Dataset checksum or row count verification failed; data may be tampered.")
        return True

    @staticmethod
    def _validate(dataset_id, source, symbol, timeframe, start, end, rows,
                  trust, ingested, label, schema_version):
        if any(not isinstance(value, str) or not value.strip()
               for value in (dataset_id, source, symbol, timeframe)):
            raise ValueError("Dataset identity, source, symbol, and timeframe are required.")
        if label not in DATASET_LABELS: raise ValueError("Dataset label is invalid.")
        if not rows: raise ValueError("Dataset rows are required.")
        if start.tzinfo is None or end.tzinfo is None or ingested.tzinfo is None or end < start:
            raise ValueError("Dataset timestamps are invalid.")
        if not isfinite(trust) or not 0 <= trust <= 1: raise ValueError("Dataset trust score is invalid.")
        if isinstance(schema_version, bool) or schema_version < 1: raise ValueError("Dataset schema version is invalid.")
        timestamps=[]
        for row in rows:
            value=row.get("timestamp") if isinstance(row,dict) else None
            if isinstance(value,str): value=datetime.fromisoformat(value)
            if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Dataset rows require timezone-aware timestamps.")
            timestamps.append(value.astimezone(timezone.utc))
        if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps): raise ValueError("Dataset rows must be strictly ordered and unique.")
        if timestamps[0] != start.astimezone(timezone.utc) or timestamps[-1] != end.astimezone(timezone.utc): raise ValueError("Dataset start or end time does not match its rows.")
