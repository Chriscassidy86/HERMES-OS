from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from core.research.provenance import DatasetCatalog
from database.research_repository import ResearchRepository
from models.research_provenance import (
    ResearchConfiguration,
    ResearchMetricSet,
    ResearchRunManifest,
)
from services.research_reproducibility import ResearchRunOrchestrator
from services.research_workspace import ResearchWorkspace


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def rows():
    return tuple(
        {
            "id": str(index),
            "timestamp": NOW + timedelta(minutes=index),
            "close": 100 + index,
        }
        for index in range(5)
    )


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = ResearchRepository(
            Path(self.temporary.name) / "research.sqlite3"
        )
        self.repository.initialize()
        DatasetCatalog(self.repository).catalog(
            dataset_id="replay",
            source="fixture",
            symbol="BTC/USD",
            timeframe="5m",
            start_time=NOW,
            end_time=NOW + timedelta(minutes=4),
            rows=rows(),
            trust_score=1,
            reliability_notes=("fixture",),
            ingested_at=NOW,
            label="REPLAY",
        )
        self.workspace = ResearchWorkspace(
            ResearchRunOrchestrator(self.repository, clock=lambda: NOW),
            self.repository,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def definition(self, run_id="RUN-1"):
        return self.workspace.define(
            run_id=run_id,
            kind="REPLAY",
            dataset_rows={"replay": rows()},
            configurations=(ResearchConfiguration("baseline", "base", 0),),
            symbols=("BTC/USD",),
            timeframes=("5m",),
        )

    def test_valid_start_manifest_and_reload(self):
        definition, data, configurations = self.definition()
        self.workspace.submit(definition, data, configurations)
        status = self.workspace.run(definition.job_id)
        self.assertEqual("COMPLETED", status.state)
        self.assertEqual("RUN-1", self.workspace.result(definition.job_id)["run_id"])

    def test_deterministic_id_and_duplicate_protection(self):
        self.assertEqual(self.definition()[0].job_id, self.definition()[0].job_id)
        definition, data, configurations = self.definition()
        self.workspace.submit(definition, data, configurations)
        with self.assertRaises(ValueError):
            self.workspace.submit(definition, data, configurations)

    def test_cancel_prevents_result_publication(self):
        definition, data, configurations = self.definition()
        self.workspace.submit(definition, data, configurations)
        self.assertEqual("CANCELLED", self.workspace.cancel(definition.job_id).state)
        self.assertEqual("CANCELLED", self.workspace.run(definition.job_id).state)
        self.assertIsNone(self.repository.load_run("RUN-1"))

    def test_failed_job_is_isolated(self):
        definition, _, configurations = self.definition()
        self.workspace.submit(definition, {"missing": rows()}, configurations)
        self.assertEqual("FAILED", self.workspace.run(definition.job_id).state)
        self.assertIsNone(self.repository.load_run("RUN-1"))

    def test_resource_bounds_and_no_configuration_mutation(self):
        with self.assertRaises(ValueError):
            self.workspace.define(
                run_id="RUN-LARGE",
                kind="REPLAY",
                dataset_rows={"replay": rows()},
                configurations=(ResearchConfiguration("base", "base", 0),),
                symbols=("BTC/USD",),
                timeframes=("5m",),
                resource_limit=1,
            )
        definition, data, configurations = self.definition()
        status = self.workspace.submit(definition, data, configurations)
        self.assertFalse(status.configuration_modified)

    def test_comparison_and_reproducibility_export(self):
        comparison = self.workspace.compare(
            ResearchMetricSet("baseline", 0, 0, 0, 0),
            ResearchMetricSet("candidate", 1, 0.1, 0.1, 0.2),
        )
        self.assertEqual(1, comparison.total_return_delta)
        manifest = ResearchRunManifest(
            "RUN-EXPORT",
            "commit",
            "configuration",
            ("replay",),
            0,
            NOW,
            NOW,
            ("BTC/USD",),
            ("5m",),
            (("workspace", "1"),),
            (("hermes", "1"),),
            ("artifact",),
            (),
            "PAPER",
            "HUMAN_REVIEW",
        )
        exported = self.workspace.export(manifest, (("python", "3"),))
        self.assertIn("RUN-EXPORT", exported.manifest_json)


if __name__ == "__main__":
    unittest.main()
