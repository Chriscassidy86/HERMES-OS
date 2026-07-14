"""Explicit activation and lookup for governed consensus sources."""

from models.consensus_registry import ConsensusSourceRecord, governed_sources
from models.market_consensus import ConsensusSource


class ConsensusSourceRegistry:
    ACTIVATABLE = {"ACTIVE_ADAPTER", "FIXTURE_ONLY", "IMPORT_ONLY"}

    def __init__(self, records: tuple[ConsensusSourceRecord, ...] | None = None, *, enabled_source_ids: tuple[str, ...] = ()):
        values = records or governed_sources()
        by_id: dict[str, ConsensusSourceRecord] = {}
        for record in values:
            if record.source_id in by_id and by_id[record.source_id] != record:
                raise ValueError("Conflicting governed source ID.")
            by_id[record.source_id] = record
        requested = set(enabled_source_ids)
        unknown = requested.difference(by_id)
        if unknown:
            raise ValueError(f"Unknown consensus source IDs: {','.join(sorted(unknown))}")
        unavailable = tuple(sorted(source_id for source_id in requested if by_id[source_id].implementation_status not in self.ACTIVATABLE))
        if unavailable:
            raise ValueError(f"Consensus sources are not activatable: {','.join(unavailable)}")
        self._records = tuple(sorted(by_id.values(), key=lambda item: item.source_id))
        self._enabled = tuple(sorted(requested))

    def records(self) -> tuple[ConsensusSourceRecord, ...]:
        return self._records

    def enabled_records(self) -> tuple[ConsensusSourceRecord, ...]:
        return tuple(item for item in self._records if item.source_id in self._enabled)

    def get(self, source_id: str) -> ConsensusSourceRecord:
        matches = tuple(item for item in self._records if item.source_id == source_id)
        if not matches:
            raise KeyError(source_id)
        return matches[0]

    def domain_source(self, source_id: str) -> ConsensusSource:
        record = self.get(source_id)
        return ConsensusSource(record.source_id, record.display_name, record.category, record.default_reliability, "GOVERNED", record.source_status, record.terms_note, source_id in self._enabled, record.known_limitations)
