from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from core.research import ExperimentService
from models.research_experiment import (
    ExperimentDefinition,
    ExperimentObservation,
    ExperimentStatus,
    HumanApproval,
)


CREATED = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def definition(**changes):
    value = ExperimentDefinition("EXP-001", "Candidate changes metric.", "score",
                                 "baseline", "candidate", "threshold 0.5 -> 0.6", CREATED)
    return replace(value, **changes)


APPROVAL = HumanApproval("research-owner", CREATED + timedelta(minutes=1), "EXP-001")


def observations(count=5):
    return tuple(ExperimentObservation(str(index), float(index), float(index) + 1,
                                       CREATED + timedelta(minutes=index + 2))
                 for index in range(count))


class ResearchExperimentTests(unittest.TestCase):
    def test_explicit_approval_is_required(self):
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), observations(), None)

    def test_evaluation_is_deterministic_and_never_applies_change(self):
        first = ExperimentService().evaluate(definition(), observations(), APPROVAL)
        second = ExperimentService().evaluate(definition(), observations(), APPROVAL)
        self.assertEqual(first, second)
        self.assertEqual(ExperimentStatus.COMPLETED, first.status)
        self.assertEqual(1.0, first.absolute_delta)
        self.assertFalse(first.production_change_applied)
        self.assertTrue(first.human_review_required)

    def test_insufficient_duplicate_or_nonfinite_samples_fail_closed(self):
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), observations(4), APPROVAL)
        duplicate = observations()[:-1] + (observations()[0],)
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), duplicate, APPROVAL)
        malformed = observations()[:-1] + (replace(observations()[-1], candidate_value=float("nan")),)
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), malformed, APPROVAL)

    def test_approval_scope_and_timing_are_enforced(self):
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), observations(), replace(APPROVAL, scope="OTHER"))
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(definition(), observations(),
                                         replace(APPROVAL, approved_at=CREATED - timedelta(seconds=1)))

    def test_live_observations_and_early_observations_are_rejected(self):
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(
                definition(), observations()[:-1] + (replace(observations()[-1], paper_only=False),), APPROVAL
            )
        with self.assertRaises(ValueError):
            ExperimentService().evaluate(
                definition(), observations()[:-1] + (replace(observations()[-1], observed_at=CREATED),), APPROVAL
            )

    def test_definition_and_result_are_immutable(self):
        result = ExperimentService().evaluate(definition(), observations(), APPROVAL)
        with self.assertRaises(FrozenInstanceError):
            result.sample_size = 99


if __name__ == "__main__":
    unittest.main()
