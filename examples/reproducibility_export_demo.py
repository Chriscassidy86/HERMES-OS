"""Export and verify one stable reproducibility manifest."""
from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from models.research_provenance import ResearchRunManifest
from services.research_reproducibility import ReproducibilityExporter
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
manifest=ResearchRunManifest("RUN-1","commit","config",("data",),7,NOW,NOW,("BTC/USD",),("5m",),(('strategy','1'),),(('trend','1'),),("artifact",),(('python','3.11'),),"PAPER","HUMAN_REVIEW")
value=ReproducibilityExporter().export(manifest,(("python","3.11"),)); print(value.manifest_json); print(value.checksum); print(value.rerun_command); print("Verified:",ReproducibilityExporter.verify(value))

