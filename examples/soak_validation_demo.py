from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from services.soak_validation import AcceleratedSoakHarness
print(AcceleratedSoakHarness().run(hours=24,symbols=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT")))
