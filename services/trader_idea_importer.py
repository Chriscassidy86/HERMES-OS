"""Safe importer for trader ideas via manual entry, JSON, and CSV.

No network access, no browser automation, no external scraping, no hidden
downloads, no credentials, and no remote execution. All validation errors are
explicit. Rejected records are never silently dropped.
"""

from datetime import datetime, timezone
import csv
import json
from math import isfinite
from pathlib import Path
from typing import Any

from models.trader_intelligence import (
    TraderEvaluationStatus,
    TraderIdeaImportSummary,
    TraderIdeaRecord,
    TraderMarketContext,
    TraderProfile,
    TraderSource,
    TraderSourceType,
    TraderSuggestedAction,
    TraderThesis,
    TraderThesisDirection,
    TraderTradePlan,
)

_MAX_FUTURE_SKEW_SECONDS = 60


def _parse_timestamp(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware.")
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware.")
        return parsed.astimezone(timezone.utc)
    raise ValueError(f"{name} must be a datetime or ISO string.")


def _parse_optional_float(value: Any, name: str, low: float | None = None) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if low is not None and value < low:
        raise ValueError(f"{name} is outside the permitted range.")
    return float(value)


def _parse_confidence(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("stated_confidence must be finite.")
    if not 0.0 <= value <= 1.0:
        raise ValueError("stated_confidence must be between 0 and 1.")
    return float(value)


def _parse_string_list(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{name} entries must be non-empty strings.")
            result.append(item)
        return tuple(result)
    raise ValueError(f"{name} must be a string or list of strings.")


def _parse_float_list(value: Any, name: str) -> tuple[float, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            parsed = _parse_optional_float(item, name, 0.0)
            if parsed is not None:
                result.append(parsed)
        return tuple(result)
    raise ValueError(f"{name} must be a list of numbers.")


class TraderIdeaImporter:
    """Import trader ideas from manual dicts, JSON files, or CSV files.

    All imports are local. No network access is performed.
    """

    def from_manual(self, record: dict[str, Any], *, ingested_at: datetime | None = None) -> TraderIdeaRecord:
        """Create a single trader idea from a manual dictionary."""
        if not isinstance(record, dict):
            raise ValueError("Manual record must be a dictionary.")
        now = (ingested_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return self._build(record, TraderSourceType.MANUAL, now)

    def from_json(self, path: str | Path, *, ingested_at: datetime | None = None) -> TraderIdeaImportSummary:
        """Import one or more trader ideas from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise ValueError("JSON file does not exist.")
        now = (ingested_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        records = data if isinstance(data, list) else [data]
        accepted: list[TraderIdeaRecord] = []
        rejected: list[tuple[int, str]] = []
        for index, raw in enumerate(records):
            try:
                accepted.append(self._build(raw, TraderSourceType.JSON_IMPORT, now))
            except Exception as exc:
                rejected.append((index, f"{type(exc).__name__}: {exc}"))
        return TraderIdeaImportSummary(tuple(accepted), tuple(rejected), TraderSourceType.JSON_IMPORT)

    def from_csv(self, path: str | Path, *, ingested_at: datetime | None = None) -> TraderIdeaImportSummary:
        """Import one or more trader ideas from a CSV file."""
        path = Path(path)
        if not path.exists():
            raise ValueError("CSV file does not exist.")
        now = (ingested_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        accepted: list[TraderIdeaRecord] = []
        rejected: list[tuple[int, str]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                try:
                    accepted.append(self._build_from_csv_row(row, now))
                except Exception as exc:
                    rejected.append((index, f"{type(exc).__name__}: {exc}"))
        return TraderIdeaImportSummary(tuple(accepted), tuple(rejected), TraderSourceType.CSV_IMPORT)

    def _build_from_csv_row(self, row: dict[str, str], ingested_at: datetime) -> TraderIdeaRecord:
        """Build a record from a CSV row, parsing semicolon-delimited list fields."""
        record: dict[str, Any] = {
            "idea_id": row.get("idea_id", ""),
            "trader_id": row.get("trader_id", ""),
            "trader_display_name": row.get("trader_display_name", ""),
            "source_id": row.get("source_id", ""),
            "source_name": row.get("source_name", ""),
            "source_reference": row.get("source_reference") or None,
            "published_at": row.get("published_at", ""),
            "symbol": row.get("symbol", ""),
            "timeframe": row.get("timeframe", ""),
            "market_regime": row.get("market_regime", ""),
            "direction": row.get("direction", ""),
            "stated_confidence": self._to_optional_float(row.get("stated_confidence"), "stated_confidence"),
            "explanation": row.get("explanation", ""),
            "supporting_evidence": self._split_csv(row.get("supporting_evidence", "")),
            "invalidation_conditions": self._split_csv(row.get("invalidation_conditions", "")),
            "assumptions": self._split_csv(row.get("assumptions", "")),
            "uncertainty": self._split_csv(row.get("uncertainty", "")),
            "entry_zone_low": self._to_optional_float(row.get("entry_zone_low"), "entry_zone_low"),
            "entry_zone_high": self._to_optional_float(row.get("entry_zone_high"), "entry_zone_high"),
            "stop_loss": self._to_optional_float(row.get("stop_loss"), "stop_loss"),
            "target_prices": self._split_csv_float(row.get("target_prices", "")),
            "suggested_action": row.get("suggested_action", ""),
            "edited_after_publication": row.get("edited_after_publication", "false").lower() in {"1", "true", "yes", "on"},
            "ingestion_label": row.get("ingestion_label", "CSV_IMPORT"),
            "attribution": row.get("attribution", ""),
            "warnings": self._split_csv(row.get("warnings", "")),
            "limitations": self._split_csv(row.get("limitations", "")),
        }
        return self._build(record, TraderSourceType.CSV_IMPORT, ingested_at)

    @staticmethod
    def _to_optional_float(value: Any, name: str) -> float | None:
        """Coerce a CSV cell to an optional finite float.

        CSV cells arrive as strings; the shared numeric validators in ``_build``
        only accept real numbers. This helper performs the deterministic string
        coercion once, preserving all existing range and finiteness checks.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = float(value.strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be a finite number.") from exc
        else:
            raise ValueError(f"{name} must be a finite number.")
        if not isfinite(parsed):
            raise ValueError(f"{name} must be finite.")
        return float(parsed)

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        if not value.strip():
            return []
        return [item.strip() for item in value.split(";") if item.strip()]

    @staticmethod
    def _split_csv_float(value: str) -> list[float]:
        if not value.strip():
            return []
        result = []
        for item in value.split(";"):
            item = item.strip()
            if not item:
                continue
            parsed = float(item)
            if not isfinite(parsed) or parsed <= 0:
                raise ValueError("target_price must be finite and positive.")
            result.append(parsed)
        return result

    def _build(self, record: dict[str, Any], source_type: TraderSourceType, ingested_at: datetime) -> TraderIdeaRecord:
        """Build a validated TraderIdeaRecord from a dictionary."""
        idea_id = self._require_str(record, "idea_id")
        trader_id = self._require_str(record, "trader_id")
        trader_display_name = self._require_str(record, "trader_display_name")
        source_id = self._require_str(record, "source_id")
        source_name = self._require_str(record, "source_name")
        source_reference = record.get("source_reference") or None
        if source_reference is not None and not isinstance(source_reference, str):
            raise ValueError("source_reference must be a string or null.")
        published_at = _parse_timestamp(record.get("published_at"), "published_at")
        symbol = self._require_str(record, "symbol")
        timeframe = self._require_str(record, "timeframe")
        market_regime = self._require_str(record, "market_regime")
        direction = self._parse_direction(record.get("direction"))
        stated_confidence = _parse_confidence(record.get("stated_confidence"))
        explanation = self._require_str(record, "explanation")
        supporting_evidence = _parse_string_list(record.get("supporting_evidence"), "supporting_evidence")
        invalidation_conditions = _parse_string_list(record.get("invalidation_conditions"), "invalidation_conditions")
        assumptions = _parse_string_list(record.get("assumptions"), "assumptions")
        uncertainty = _parse_string_list(record.get("uncertainty"), "uncertainty")
        entry_zone_low = _parse_optional_float(record.get("entry_zone_low"), "entry_zone_low", 0.0)
        entry_zone_high = _parse_optional_float(record.get("entry_zone_high"), "entry_zone_high", 0.0)
        stop_loss = _parse_optional_float(record.get("stop_loss"), "stop_loss", 0.0)
        target_prices = _parse_float_list(record.get("target_prices"), "target_prices")
        suggested_action = self._parse_action(record.get("suggested_action"))
        edited_after_publication = bool(record.get("edited_after_publication", False))
        ingestion_label = self._require_str(record, "ingestion_label") if record.get("ingestion_label") else source_type.value
        attribution = self._require_str(record, "attribution")
        warnings = _parse_string_list(record.get("warnings"), "warnings")
        limitations = _parse_string_list(record.get("limitations"), "limitations")
        evaluation_status_str = record.get("evaluation_status", "PENDING")
        try:
            evaluation_status = TraderEvaluationStatus(evaluation_status_str)
        except ValueError as exc:
            raise ValueError(f"evaluation_status is invalid: {evaluation_status_str}") from exc

        if published_at > ingested_at and (published_at - ingested_at).total_seconds() > _MAX_FUTURE_SKEW_SECONDS:
            raise ValueError("Publication timestamp cannot be unreasonably future-dated.")

        trader = TraderProfile(trader_id, trader_display_name, attribution)
        source = TraderSource(source_id, source_name, source_type, source_reference, "IMPORT", "Local import", limitations)
        context = TraderMarketContext(symbol, timeframe, market_regime)
        thesis = TraderThesis(direction, stated_confidence, explanation, supporting_evidence, invalidation_conditions, assumptions, uncertainty)
        plan = TraderTradePlan(entry_zone_low, entry_zone_high, stop_loss, target_prices)

        return TraderIdeaRecord.create(
            idea_id=idea_id,
            trader=trader,
            source=source,
            published_at=published_at,
            ingested_at=ingested_at,
            context=context,
            thesis=thesis,
            trade_plan=plan,
            suggested_action=suggested_action,
            edited_after_publication=edited_after_publication,
            ingestion_label=ingestion_label,
            warnings=warnings,
            limitations=limitations,
            evaluation_status=evaluation_status,
        )

    @staticmethod
    def _require_str(record: dict[str, Any], name: str) -> str:
        value = record.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required.")
        return value.strip()

    @staticmethod
    def _parse_direction(value: Any) -> TraderThesisDirection:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("direction is required.")
        try:
            return TraderThesisDirection(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"direction is not a supported thesis: {value}") from exc

    @staticmethod
    def _parse_action(value: Any) -> TraderSuggestedAction:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("suggested_action is required.")
        try:
            return TraderSuggestedAction(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"suggested_action is not supported: {value}") from exc
