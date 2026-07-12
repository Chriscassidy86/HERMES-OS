"""Foundation IV.4 SQLite audit journal tests."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3, tempfile, unittest
from core.decision_cycle import DecisionCycle
from database.journal import DuplicateCycleError, SCHEMA_VERSION, SchemaVersionError, SQLiteAuditJournal, TABLES
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot

NOW=datetime(2026,7,11,12,tzinfo=timezone.utc)
def cycle(trend="Bullish"):
    directional=trend in {"Bullish","Bearish"}
    snap=MarketSnapshot("BTC/USD",102.0 if directional else 100.0,1500.0 if directional else 1000.0,trend,2.0 if directional else 4.0,55,
        100.0,1000.0,101.0 if directional else 100.0,99.0 if directional else 100.0,"4H",NOW)
    return DecisionCycle(clock=lambda:NOW).run(snap)

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/"audit.sqlite3"
        self.journal=SQLiteAuditJournal(self.path); self.journal.initialize()
    def tearDown(self): self.tmp.cleanup()
    def test_initialize_clean_database(self):
        with self.journal.connect() as db:
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(set(TABLES).issubset(names)); self.assertEqual(SCHEMA_VERSION,1)
    def test_persist_and_reload_cycle(self):
        result=cycle(); self.journal.save_cycle(result); loaded=self.journal.load_cycle(result.cycle_id)
        self.assertEqual(result.cycle_id,loaded["cycle_id"]); self.assertTrue(loaded["paper_execution_eligible"])
    def test_persist_rejected_cycle(self):
        result=cycle("Sideways"); self.journal.save_cycle(result)
        self.assertFalse(self.journal.load_cycle(result.cycle_id)["paper_execution_eligible"]); self.assertTrue(self.journal.rejection_history())
    def test_persist_order_lifecycle(self):
        result=cycle(); book=PaperPortfolio(clock=lambda:NOW); order=book.propose(result,102); book.execute_market(order.order_id)
        self.journal.save_portfolio(book,result.cycle_id)
        with self.journal.connect() as db: count=db.execute("SELECT COUNT(*) FROM paper_orders").fetchone()[0]
        self.assertEqual(1,count)
    def test_duplicate_cycle_rejected(self):
        result=cycle(); self.journal.save_cycle(result)
        with self.assertRaises(DuplicateCycleError): self.journal.save_cycle(result)
    def test_transaction_rolls_back(self):
        class FailingJournal(SQLiteAuditJournal):
            def _insert_cycle_details(self,db,result,created): raise RuntimeError("forced")
        journal=FailingJournal(self.path)
        with self.assertRaises(RuntimeError): journal.save_cycle(cycle())
        self.assertEqual([],journal.recent_cycles())
    def test_reload_portfolio_state(self):
        result=cycle(); book=PaperPortfolio(clock=lambda:NOW); order=book.propose(result,102); book.execute_market(order.order_id)
        self.journal.save_portfolio(book,result.cycle_id); loaded=self.journal.current_portfolio()
        self.assertEqual("9979.97",loaded["account"]["cash_balance"])
    def test_schema_version_validation(self):
        with self.journal.connect() as db: db.execute("UPDATE schema_metadata SET version=999")
        with self.assertRaises(SchemaVersionError): self.journal.validate_schema()
    def test_same_timestamp_portfolio_history_is_not_overwritten(self):
        result=cycle(); book=PaperPortfolio(clock=lambda:NOW); order=book.propose(result,102); book.execute_market(order.order_id)
        self.journal.save_portfolio(book,"cycle-one"); book.cash-=1; self.journal.save_portfolio(book,"cycle-two")
        with self.journal.connect() as db:
            snapshots=db.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0]
            positions=db.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        self.assertEqual(2,snapshots); self.assertEqual(2,positions); self.assertEqual(str(book.account().cash_balance),self.journal.current_portfolio()["account"]["cash_balance"])
if __name__=="__main__": unittest.main()
