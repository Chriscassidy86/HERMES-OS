"""See tests/test_multi_symbol_scheduler.py for the deterministic four-symbol fixture."""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from models.multi_symbol import SymbolSchedule
print(tuple(SymbolSchedule(symbol) for symbol in ("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT")))
