"""Initialize SQLite and save one deterministic paper-only decision cycle."""
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from reports.market_snapshot import MarketSnapshot
now=datetime.now(timezone.utc)
snapshot=MarketSnapshot("BTC/USD",108000,42_500_000_000,"Bullish",2.8,74,106000,35_000_000_000,107500,104000,"4H",now)
result=DecisionCycle(clock=lambda:now).run(snapshot)
path=ROOT/"data"/"hermes_audit.sqlite3"; journal=SQLiteAuditJournal(path); journal.initialize(); journal.save_cycle(result)
print("PAPER MODE ONLY"); print("Database:",path); print("Saved cycle:",result.cycle_id); print("Recent cycles:",len(journal.recent_cycles())); print("Exchange contacted: False")
