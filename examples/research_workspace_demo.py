"""Create a bounded PAPER research job definition without running it."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from models.research_provenance import ResearchConfiguration
from services.research_workspace import ResearchWorkspace


class EmptyRepository:
    @staticmethod
    def load_run(_run_id):
        return None


workspace = ResearchWorkspace(orchestrator=None, repository=EmptyRepository())
definition, _rows, _configurations = workspace.define(
    run_id="DEMO-REPLAY-1",
    kind="REPLAY",
    dataset_rows={"fixture": ({"close": 100}, {"close": 101})},
    configurations=(ResearchConfiguration("baseline", "demo-v1", 0),),
    symbols=("BTC/USD",),
    timeframes=("5m",),
)
print(definition)
