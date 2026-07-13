"""SQLite audit journal. Importing this module performs no database writes."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from itertools import count
import json
from pathlib import Path
import sqlite3

SCHEMA_VERSION=1
TABLES=("decision_cycles","snapshots","specialist_reports","evidence_summaries",
 "recommendations","risk_assessments","paper_orders","fills","positions","trades",
 "portfolio_snapshots","rejection_reasons")

class DuplicateCycleError(ValueError): pass
class SchemaVersionError(RuntimeError): pass
class ClosingConnection(sqlite3.Connection):
    def __exit__(self,exc_type,exc_value,traceback):
        try: return super().__exit__(exc_type,exc_value,traceback)
        finally: self.close()

def _json_default(value):
    if is_dataclass(value): return asdict(value)
    if isinstance(value,datetime): return value.astimezone(timezone.utc).isoformat()
    if isinstance(value,Decimal): return str(value)
    if isinstance(value,Enum): return value.value
    raise TypeError(f"Unsupported audit value: {type(value).__name__}")
def serialize(value): return json.dumps(value,default=_json_default,sort_keys=True,separators=(",",":"))

class SQLiteAuditJournal:
    def __init__(self,path): self.path=Path(path)
    def connect(self):
        connection=sqlite3.connect(self.path,factory=ClosingConnection)
        connection.row_factory=sqlite3.Row; connection.execute("PRAGMA foreign_keys=ON")
        return connection
    def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schema_metadata (version INTEGER NOT NULL)")
            row=db.execute("SELECT version FROM schema_metadata").fetchone()
            if row is None: db.execute("INSERT INTO schema_metadata VALUES (?)",(SCHEMA_VERSION,))
            elif row[0]!=SCHEMA_VERSION: raise SchemaVersionError(f"Expected schema {SCHEMA_VERSION}, found {row[0]}")
            db.execute("CREATE TABLE IF NOT EXISTS decision_cycles (cycle_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, eligible INTEGER NOT NULL, payload TEXT NOT NULL)")
            for table in TABLES[1:]:
                if table in {"paper_orders","fills","positions","trades","portfolio_snapshots"}:
                    db.execute(f"CREATE TABLE IF NOT EXISTS {table} (record_id TEXT PRIMARY KEY, cycle_id TEXT, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
                else:
                    db.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL, FOREIGN KEY(cycle_id) REFERENCES decision_cycles(cycle_id) ON DELETE CASCADE)")
    def validate_schema(self):
        with self.connect() as db:
            row=db.execute("SELECT version FROM schema_metadata").fetchone()
            if row is None or row[0]!=SCHEMA_VERSION: raise SchemaVersionError("Database schema version is invalid.")
    def save_cycle(self,result):
        created=result.timestamp.astimezone(timezone.utc).isoformat()
        try:
            with self.connect() as db:
                db.execute("INSERT INTO decision_cycles VALUES (?,?,?,?,?)",(result.cycle_id,created,result.final_status,int(result.paper_execution_eligible),serialize(result)))
                self._insert_cycle_details(db,result,created)
        except sqlite3.IntegrityError as exc:
            raise DuplicateCycleError(result.cycle_id) from exc
    def _insert_cycle_details(self,db,result,created):
        rows=(("snapshots",result.snapshot),("evidence_summaries",result.evidence_summary),
              ("recommendations",result.recommendation),("risk_assessments",result.risk_assessment))
        for table,value in rows: db.execute(f"INSERT INTO {table}(cycle_id,created_at,payload) VALUES(?,?,?)",(result.cycle_id,created,serialize(value)))
        for report in result.specialist_reports: db.execute("INSERT INTO specialist_reports(cycle_id,created_at,payload) VALUES(?,?,?)",(result.cycle_id,created,serialize(report)))
        for reason in result.rejection_reasons: db.execute("INSERT INTO rejection_reasons(cycle_id,created_at,payload) VALUES(?,?,?)",(result.cycle_id,created,serialize({"reason":reason})))
    def save_portfolio(self,portfolio,cycle_id=None):
        now=portfolio.clock().astimezone(timezone.utc).isoformat()
        with self.connect() as db:
            for table,records,key in (("paper_orders",portfolio.orders.values(),"order_id"),("fills",portfolio.fills.values(),"fill_id"),("positions",portfolio.positions.values(),"symbol"),("trades",portfolio.trades,"trade_id")):
                for record in records:
                    rid=getattr(record,key)
                    if table=="positions": rid=f"{cycle_id or 'none'}:{rid}"
                    db.execute(f"INSERT OR REPLACE INTO {table} VALUES(?,?,?,?)",(rid,cycle_id,now,serialize(record)))
            rid=f"portfolio-{cycle_id or 'none'}-{now}-{len(portfolio.transitions)}-{len(portfolio.trades)}"
            payload={"account":portfolio.account(),"positions":tuple(portfolio.positions.values()),
                     "orders":tuple(portfolio.orders.values()),"fills":tuple(portfolio.fills.values()),
                     "trades":tuple(portfolio.trades),"transitions":tuple(portfolio.transitions)}
            db.execute("INSERT OR REPLACE INTO portfolio_snapshots VALUES(?,?,?,?)",(rid,cycle_id,now,serialize(payload)))
    def load_cycle(self,cycle_id):
        with self.connect() as db:
            row=db.execute("SELECT payload FROM decision_cycles WHERE cycle_id=?",(cycle_id,)).fetchone()
        return json.loads(row[0]) if row else None
    def recent_cycles(self,limit=20): return self._query("SELECT payload FROM decision_cycles ORDER BY created_at DESC LIMIT ?",(limit,))
    def paper_trades(self,limit=20): return self._query("SELECT payload FROM trades ORDER BY created_at DESC LIMIT ?",(limit,))
    def current_portfolio(self):
        rows=self._query("SELECT payload FROM portfolio_snapshots ORDER BY created_at DESC, rowid DESC LIMIT 1")
        return rows[0] if rows else None
    def portfolio_history(self,limit=200):
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=1000: raise ValueError("Portfolio history limit is invalid.")
        with self.connect() as db:
            rows=db.execute("SELECT created_at,payload FROM portfolio_snapshots ORDER BY created_at DESC,rowid DESC LIMIT ?",(limit,)).fetchall()
        result=[]
        for row in rows:
            payload=json.loads(row[1]); payload["recorded_at"]=row[0]; result.append(payload)
        return result
    def restore_portfolio(self,portfolio):
        from paper_trading.models import (OrderStatus,OrderTransition,PaperFill,
            PaperOrder,PaperPosition,PaperTrade)
        state=self.current_portfolio()
        if state is None: return False
        portfolio.cash=Decimal(state["account"]["cash_balance"])
        portfolio.positions={item["symbol"]:PaperPosition(item["symbol"],Decimal(item["quantity"]),Decimal(item["average_entry_price"]),Decimal(item["current_price"]),Decimal(item["entry_fees"])) for item in state["positions"]}
        portfolio.orders={item["order_id"]:PaperOrder(item["order_id"],item["cycle_id"],item["symbol"],item["side"],Decimal(item["quantity"]),Decimal(item["reference_price"]),OrderStatus(item["status"]),datetime.fromisoformat(item["created_at"]),tuple(item.get("rejection_reasons",()))) for item in state.get("orders",())}
        portfolio.fills={item["fill_id"]:PaperFill(item["fill_id"],item["order_id"],Decimal(item["quantity"]),Decimal(item["price"]),Decimal(item["fee"]),Decimal(item["slippage"]),datetime.fromisoformat(item["timestamp"])) for item in state.get("fills",())}
        portfolio.trades=[PaperTrade(item["trade_id"],item["symbol"],Decimal(item["quantity"]),Decimal(item["entry_price"]),Decimal(item["exit_price"]),Decimal(item["fees"]),Decimal(item["realized_pnl"]),datetime.fromisoformat(item["closed_at"])) for item in state.get("trades",())]
        portfolio.transitions=[OrderTransition(item["order_id"],OrderStatus(item["previous_status"]),OrderStatus(item["new_status"]),datetime.fromisoformat(item["timestamp"]),item["reason"]) for item in state.get("transitions",())]
        next_trade=max((int(item.trade_id.removeprefix("PT-")) for item in portfolio.trades),default=0)+1
        portfolio._ids=count(next_trade)
        return True
    def rejection_history(self,limit=20): return self._query("SELECT payload FROM rejection_reasons ORDER BY id DESC LIMIT ?",(limit,))
    def _query(self,sql,params=()):
        with self.connect() as db: rows=db.execute(sql,params).fetchall()
        return [json.loads(row[0]) for row in rows]
