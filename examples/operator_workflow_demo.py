"""Show the local PAPER operator checklist and one alert."""
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from services.operator_workflow import DailyOperatorWorkflow, LocalAlertManager
now = datetime.now(timezone.utc); manager = LocalAlertManager()
print(manager.create(category="MISSING_BRIEFING", severity="WARNING", message="The latest briefing is missing.", created_at=now))
print(DailyOperatorWorkflow().complete(1, completed_at=now))
