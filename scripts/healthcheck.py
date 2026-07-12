from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.settings import RuntimeSettings
from core.health import StartupChecks
settings=RuntimeSettings.from_env(); summary=StartupChecks(settings).run()
print("PAPER MODE" if summary.healthy else "UNHEALTHY"); raise SystemExit(0 if summary.healthy else 1)
