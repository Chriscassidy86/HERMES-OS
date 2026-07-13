"""Risk-gated facade over the existing deterministic paper portfolio."""
from models.paper_execution import PaperExecutionOutcome

class PaperExecutionEngine:
    def __init__(self, portfolio): self.portfolio = portfolio
    def execute(self, cycle, price):
        recommendation=cycle.recommendation; risk=cycle.risk_assessment
        action={"LONG":"BUY","SHORT":"SELL","HOLD":"HOLD","WAIT":"WAIT"}.get(recommendation.action,"WAIT")
        reports=tuple(item.summary() for item in cycle.specialist_reports)
        regime=getattr(cycle.snapshot,"market_trend","UNKNOWN")
        explanation=recommendation.reason
        order=fill=trade=None; duration=None; status="NO_ACTION"
        if not risk.approved: status="RISK_REJECTED"
        elif action=="BUY" and cycle.paper_execution_eligible:
            order=self.portfolio.propose(cycle,price)
            if order.status.value=="VALIDATED": order,fill=self.portfolio.execute_market(order.order_id); status="PAPER_FILLED"
            else: status="PAPER_REJECTED"
        elif action=="SELL" and cycle.snapshot.symbol in self.portfolio.positions:
            entries=tuple(item.timestamp for item in self.portfolio.fills.values() if self.portfolio.orders[item.order_id].symbol==cycle.snapshot.symbol)
            trade=self.portfolio.close_position(cycle.snapshot.symbol,price); status="PAPER_CLOSED"
            if entries: duration=(trade.closed_at-min(entries)).total_seconds()
        return PaperExecutionOutcome(action,status,cycle.snapshot.symbol,cycle.timestamp,recommendation.confidence,risk.approved,risk.reason,regime,reports,explanation,order,fill,trade,duration)
