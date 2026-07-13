"""Risk-gated facade over the existing deterministic paper portfolio."""
from math import isfinite
from dataclasses import replace
from models.paper_execution import PaperExecutionOutcome,SimulatedFill,SimulatedOrder,SimulationRules

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

class RealisticPaperSimulator:
    TYPES={"MARKET","LIMIT","STOP_LOSS","TAKE_PROFIT","TRAILING_STOP"}
    def __init__(self,rules=SimulationRules()): self.rules=rules; self.orders={}; self.fills={}; self._validate_rules()
    def submit(self,cycle,*,side,order_type,quantity,market_price,limit_price=None,stop_price=None,trailing_percent=None,elapsed_ms=0,source="PAPER"):
        if not cycle.risk_assessment.approved: raise ValueError("Risk rejection prevents simulated order creation.")
        values=(quantity,market_price,elapsed_ms)
        if side not in {"BUY","SELL"} or order_type not in self.TYPES or any(isinstance(x,bool) or not isfinite(x) or x<0 for x in values): raise ValueError("Simulation inputs are invalid.")
        quantity=round(quantity,self.rules.quantity_precision); market_price=round(market_price,self.rules.price_precision)
        if quantity<self.rules.minimum_quantity or quantity*market_price<self.rules.minimum_notional: raise ValueError("Minimum quantity or notional rejected.")
        oid=f"SIM-{cycle.cycle_id}-{len(self.orders)+1}"
        order=SimulatedOrder(oid,cycle.cycle_id,cycle.snapshot.symbol,side,order_type,quantity,"OPEN",cycle.timestamp,True,limit_price,stop_price,trailing_percent)
        if elapsed_ms>self.rules.timeout_ms:
            order=replace(order,status="TIMED_OUT"); self.orders[oid]=order; return order,()
        triggered=self._triggered(order,market_price)
        if not triggered: self.orders[oid]=order; return order,()
        ratio=self.rules.partial_fill_ratio; filled=round(quantity*ratio,self.rules.quantity_precision)
        if filled<=0 or filled>quantity: raise ValueError("Partial fill cannot overfill or round to zero.")
        direction=1 if side=="BUY" else -1
        bps=self.rules.spread_bps/2+self.rules.slippage_bps+self.rules.impact_bps_per_unit*filled
        price=round(market_price*(1+direction*bps/10000),self.rules.price_precision)
        fee=round(filled*price*self.rules.fee_bps/10000,self.rules.price_precision)
        fill=SimulatedFill(f"F-{oid}",oid,cycle.cycle_id,source,cycle.timestamp,filled,price,fee,round(abs(price-market_price),self.rules.price_precision),self.rules.latency_ms,f"Deterministic {order_type} PAPER fill with spread, slippage and market impact.")
        order=replace(order,status="FILLED" if filled==quantity else "PARTIALLY_FILLED")
        self.orders[oid]=order; self.fills[fill.fill_id]=fill; return order,(fill,)
    def cancel(self,order_id):
        order=self.orders[order_id]
        if order.status not in {"OPEN","PARTIALLY_FILLED"}: raise ValueError("Only active simulated orders may cancel.")
        order=replace(order,status="CANCELLED"); self.orders[order_id]=order; return order
    def _triggered(self,order,price):
        if order.order_type=="MARKET": return True
        if order.order_type=="LIMIT":
            if order.limit_price is None or not isfinite(order.limit_price): raise ValueError("Limit price is required.")
            return price<=order.limit_price if order.side=="BUY" else price>=order.limit_price
        if order.order_type in {"STOP_LOSS","TAKE_PROFIT"}:
            if order.stop_price is None or not isfinite(order.stop_price): raise ValueError("Stop price is required.")
            adverse=price<=order.stop_price if order.side=="SELL" else price>=order.stop_price
            return adverse if order.order_type=="STOP_LOSS" else not adverse
        if order.trailing_percent is None or not isfinite(order.trailing_percent) or order.trailing_percent<=0: raise ValueError("Trailing percent is required.")
        return True
    def _validate_rules(self):
        numeric=(self.rules.spread_bps,self.rules.slippage_bps,self.rules.impact_bps_per_unit,self.rules.minimum_quantity,self.rules.minimum_notional,self.rules.fee_bps)
        if any(not isfinite(x) or x<0 for x in numeric) or not 0<self.rules.partial_fill_ratio<=1 or self.rules.timeout_ms<0 or self.rules.latency_ms<0: raise ValueError("Simulation rules are invalid.")
