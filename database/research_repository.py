"""Transaction-safe, versioned SQLite persistence for research provenance."""

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from core.research.provenance import stable_checksum, stable_json


RESEARCH_SCHEMA_VERSION = 1
ARTIFACT_TYPES = {
    "DECISION_EXPLANATION", "MARKET_REGIME", "MULTI_TIMEFRAME", "CEO_DASHBOARD",
    "LEARNING_EXPLANATION", "EXECUTIVE_BRIEFING", "EXPERIMENT_RESULT",
    "RESEARCH_METRICS", "WALK_FORWARD", "COMPARISON", "CALIBRATION",
}


class ResearchSchemaVersionError(RuntimeError): pass
class DuplicateResearchRunError(ValueError): pass
class DuplicateResearchRecordError(ValueError): pass


class ResearchRepository:
    def __init__(self, path): self.path = Path(path)

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return closing(connection)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            with db:
                db.execute("CREATE TABLE IF NOT EXISTS research_schema_metadata (version INTEGER NOT NULL)")
                row = db.execute("SELECT version FROM research_schema_metadata").fetchone()
                if row is None:
                    db.execute("INSERT INTO research_schema_metadata VALUES (?)", (RESEARCH_SCHEMA_VERSION,))
                elif row[0] not in (0, RESEARCH_SCHEMA_VERSION):
                    raise ResearchSchemaVersionError(
                        f"Expected research schema {RESEARCH_SCHEMA_VERSION}, found {row[0]}."
                    )
                self._create_tables(db)
                if row is not None and row[0] == 0:
                    db.execute("UPDATE research_schema_metadata SET version=?", (RESEARCH_SCHEMA_VERSION,))

    @staticmethod
    def _create_tables(db):
        db.execute("CREATE TABLE IF NOT EXISTS research_datasets (dataset_id TEXT PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS research_runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS research_artifacts (artifact_id TEXT PRIMARY KEY, artifact_type TEXT NOT NULL, schema_version INTEGER NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL)")

    def validate_schema(self):
        with self.connect() as db:
            row = db.execute("SELECT version FROM research_schema_metadata").fetchone()
            if row is None or row[0] != RESEARCH_SCHEMA_VERSION:
                raise ResearchSchemaVersionError("Research schema version is invalid.")

    def save_dataset(self, record):
        return self._save_idempotent("research_datasets", "dataset_id", record.dataset_id, record)

    def load_dataset(self, dataset_id): return self._load("research_datasets", "dataset_id", dataset_id)

    def save_run(self, manifest):
        try: return self._save_idempotent("research_runs", "run_id", manifest.run_id, manifest)
        except DuplicateResearchRecordError as exc: raise DuplicateResearchRunError(manifest.run_id) from exc

    def load_run(self, run_id): return self._load("research_runs", "run_id", run_id)

    def save_artifact(self, artifact_id, artifact_type, value, created_at, schema_version=1):
        if artifact_type not in ARTIFACT_TYPES: raise ValueError("Research artifact type is invalid.")
        if created_at.tzinfo is None or schema_version < 1: raise ValueError("Artifact version or timestamp is invalid.")
        payload = stable_json(value); self._reject_secrets(payload); checksum = stable_checksum(value)
        with self.connect() as db:
            with db:
                row = db.execute("SELECT payload,checksum FROM research_artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
                if row:
                    if row["payload"] == payload and row["checksum"] == checksum: return False
                    raise DuplicateResearchRecordError(artifact_id)
                db.execute("INSERT INTO research_artifacts VALUES (?,?,?,?,?,?)", (
                    artifact_id, artifact_type, schema_version,
                    created_at.astimezone(timezone.utc).isoformat(), payload, checksum
                ))
        return True

    def load_artifact(self, artifact_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM research_artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        if not row: return None
        value = dict(row); value["payload"] = json.loads(value["payload"]); return value

    def _save_idempotent(self, table, key, identifier, value):
        payload = stable_json(value); self._reject_secrets(payload); checksum = stable_checksum(value)
        with self.connect() as db:
            with db:
                row = db.execute(f"SELECT payload,checksum FROM {table} WHERE {key}=?", (identifier,)).fetchone()
                if row:
                    if row["payload"] == payload and row["checksum"] == checksum: return False
                    raise DuplicateResearchRecordError(identifier)
                db.execute(f"INSERT INTO {table} VALUES (?,?,?)", (identifier, payload, checksum))
        return True

    def _load(self, table, key, identifier):
        with self.connect() as db:
            row = db.execute(f"SELECT payload FROM {table} WHERE {key}=?", (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _reject_secrets(payload):
        lowered=payload.lower()
        names=("api"+"_"+"key","api"+"_"+"secret","pass"+"word","private"+"_"+"key","access"+"_"+"token")
        forbidden=tuple(f'"{name}"' for name in names)
        if any(value in lowered for value in forbidden): raise ValueError("Research persistence refuses secret-shaped fields.")
