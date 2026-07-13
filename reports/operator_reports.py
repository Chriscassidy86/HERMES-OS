"""Read-only local operator reports built from journal/application services."""
import json
from decimal import Decimal
from agents.performance.performance_engine import PerformanceEngine

class OperatorReports:
    def __init__(self,journal,provider=None): self.journal=journal; self.provider=provider
    def system_status(self):
        cycles=self.journal.recent_cycles(1)
        return {"mode":"PAPER","database":"HEALTHY","latest_cycle_id":cycles[0]["cycle_id"] if cycles else None,"provider":self.provider_health()}
    def latest_decision_cycle(self):
        rows=self.journal.recent_cycles(1); return rows[0] if rows else None
    def latest_evidence_summary(self):
        cycle=self.latest_decision_cycle(); return cycle["evidence_summary"] if cycle else None
    def current_paper_portfolio(self): return self.journal.current_portfolio()
    def open_positions(self):
        portfolio=self.current_paper_portfolio(); return portfolio["positions"] if portfolio else []
    def completed_trades(self,limit=20): return self.journal.paper_trades(limit)
    def daily_pnl(self):
        trades=self.completed_trades(); return {"completed_trades":len(trades),"realized_pnl":str(sum((Decimal(t["realized_pnl"]) for t in trades),Decimal("0")))}
    def agent_scorecards(self,outcomes):
        return [card.__dict__ for card in PerformanceEngine().specialist_scorecards(outcomes)]
    def rejected_decisions(self,limit=20): return self.journal.rejection_history(limit)
    def risk_state(self):
        cycle=self.latest_decision_cycle(); return cycle["risk_assessment"] if cycle else {"approved":False,"reason":"No decision cycle available."}
    def provider_health(self):
        health=getattr(self.provider,"health",None)
        return {"healthy":health.healthy,"status":health.status,"last_error":health.last_error} if health else {"healthy":False,"status":"NOT_CONFIGURED","last_error":None}
    @staticmethod
    def to_json(value): return json.dumps(value,indent=2,sort_keys=True)
