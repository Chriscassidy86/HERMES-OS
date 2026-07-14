from dataclasses import FrozenInstanceError, replace
import unittest

from models.consensus_registry import ConsensusSourceRecord, governed_sources
from services.consensus_source_registry import ConsensusSourceRegistry


class ConsensusRegistryTests(unittest.TestCase):
    def test_catalog_covers_governed_source_states_without_default_activation(self):
        registry = ConsensusSourceRegistry()
        statuses = {item.source_status for item in registry.records()}
        self.assertTrue({"PUBLIC", "FIXTURE", "EXPORT", "UNAVAILABLE", "LICENSED"}.issubset(statuses))
        self.assertEqual((), registry.enabled_records())
        self.assertTrue(all(not item.enabled_by_default for item in registry.records()))

    def test_activation_is_explicit_and_deterministic(self):
        registry = ConsensusSourceRegistry(enabled_source_ids=("derivatives-fixture", "hermes-public-market"))
        self.assertEqual(("derivatives-fixture", "hermes-public-market"), tuple(item.source_id for item in registry.enabled_records()))
        self.assertTrue(registry.domain_source("hermes-public-market").enabled)

    def test_unavailable_deferred_or_unconfigured_source_cannot_activate(self):
        for source_id in ("fear-greed-public", "coingecko-public-metadata", "licensed-onchain-unconfigured"):
            with self.assertRaisesRegex(ValueError, "not activatable"):
                ConsensusSourceRegistry(enabled_source_ids=(source_id,))

    def test_unknown_and_conflicting_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            ConsensusSourceRegistry(enabled_source_ids=("not-registered",))
        first = governed_sources()[0]
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            ConsensusSourceRegistry((first, replace(first, display_name="Conflict")))

    def test_records_are_immutable_and_contain_no_secret_fields(self):
        item = governed_sources()[0]
        with self.assertRaises(FrozenInstanceError):
            item.display_name = "Changed"
        field_names = tuple(ConsensusSourceRecord.__dataclass_fields__)
        self.assertFalse(any(term in name.lower() for name in field_names for term in ("secret", "password", "token")))

    def test_fixture_import_and_public_access_are_distinct(self):
        by_id = {item.source_id: item for item in governed_sources()}
        self.assertEqual("DETERMINISTIC_FIXTURE", by_id["derivatives-fixture"].approved_access_method)
        self.assertEqual("MANUAL_IMPORT", by_id["analyst-community-import"].approved_access_method)
        self.assertEqual("EXISTING_VALIDATED_SNAPSHOT", by_id["hermes-public-market"].approved_access_method)


if __name__ == "__main__":
    unittest.main()
