"""Deterministic in-memory paper portfolio with audited order transitions."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from itertools import count

from models.cycle_result import DecisionCycleResult
from paper_trading.models import (OrderStatus, OrderTransition, PaperAccount,
    PaperFill, PaperOrder, PaperPosition, PaperTrade)

CENT=Decimal("0.01"); QTY=Decimal("0.00000001")
ALLOWED={
 OrderStatus.CREATED:{OrderStatus.VALIDATED,OrderStatus.REJECTED},
 OrderStatus.VALIDATED:{OrderStatus.OPEN,OrderStatus.REJECTED},
 OrderStatus.OPEN:{OrderStatus.PARTIALLY_FILLED,OrderStatus.FILLED,OrderStatus.CANCELLED},
 OrderStatus.PARTIALLY_FILLED:{OrderStatus.PARTIALLY_FILLED,OrderStatus.FILLED,OrderStatus.CANCELLED},
 OrderStatus.FILLED:{OrderStatus.CLOSED}, OrderStatus.REJECTED:set(),
 OrderStatus.CANCELLED:set(), OrderStatus.CLOSED:set(),
}

class PaperPortfolio:
    def __init__(self, starting_cash=Decimal("10000"), fee_bps=Decimal("10"), slippage_bps=Decimal("5"), clock=None):
        self.starting_cash=Decimal(starting_cash); self.cash=self.starting_cash
        self.fee_bps=Decimal(fee_bps); self.slippage_bps=Decimal(slippage_bps)
        if not self.starting_cash.is_finite() or self.starting_cash <= 0:
            raise ValueError("Starting cash must be finite and positive.")
        if not self.fee_bps.is_finite() or self.fee_bps < 0:
            raise ValueError("Fee basis points must be finite and non-negative.")
        if not self.slippage_bps.is_finite() or self.slippage_bps < 0:
            raise ValueError("Slippage basis points must be finite and non-negative.")
        self.clock=clock or (lambda: datetime.now(timezone.utc)); self.positions={}
        self.orders={}; self.fills={}; self.trades=[]; self.transitions=[]; self._ids=count(1)

    def account(self):
        equity=self.cash+sum((p.market_value for p in self.positions.values()),Decimal("0"))
        return PaperAccount(self.cash.quantize(CENT),equity.quantize(CENT))

    def propose(self, result: DecisionCycleResult, price, notional=None):
        now=self.clock(); oid=f"PO-{result.cycle_id}"; price=Decimal(str(price))
        if oid in self.orders: raise ValueError("A paper order already exists for this decision cycle.")
        cap=Decimal(str(result.risk_assessment.max_position_size)); amount=Decimal(str(notional)) if notional is not None else cap
        reasons=[]
        if not result.paper_execution_eligible: reasons.append("Decision cycle is not paper-execution eligible.")
        if not result.risk_assessment.approved: reasons.append("Risk Manager vetoed the trade.")
        if result.recommendation.action not in {"LONG","SHORT"}: reasons.append("Recommendation is not directional.")
        if result.recommendation.action=="SHORT": reasons.append("Simulated short positions are not supported safely yet.")
        if not price.is_finite() or price<=0: reasons.append("Execution price must be finite and greater than zero.")
        if not amount.is_finite() or not cap.is_finite() or amount<=0 or amount>cap: reasons.append("Position size is invalid or exceeds the Risk Manager cap.")
        if result.snapshot.symbol in self.positions: reasons.append("An open position already exists for this symbol.")
        qty=(amount/price).quantize(QTY,rounding=ROUND_DOWN) if price.is_finite() and price>0 and amount.is_finite() else Decimal("0")
        if qty<=0: reasons.append("Position size rounds to zero quantity.")
        order=PaperOrder(oid,result.cycle_id,result.snapshot.symbol,"BUY",qty,price,OrderStatus.CREATED,now)
        self.orders[oid]=order
        if reasons: return self._transition(order,OrderStatus.REJECTED," ".join(reasons),tuple(reasons))
        return self._transition(order,OrderStatus.VALIDATED,"All paper safety checks passed.")

    def execute_market(self, order_id):
        order=self.orders[order_id]
        if order.status!=OrderStatus.VALIDATED: raise ValueError("Only validated orders may execute.")
        if order.symbol in self.positions:
            return self._transition(order,OrderStatus.REJECTED,"An open position already exists for this symbol.",("An open position already exists for this symbol.",))
        order=self._transition(order,OrderStatus.OPEN,"Opened for deterministic simulated fill.")
        fill_price=(order.reference_price*(Decimal("1")+self.slippage_bps/Decimal("10000"))).quantize(CENT)
        notional=order.quantity*fill_price; fee=(notional*self.fee_bps/Decimal("10000")).quantize(CENT)
        if self.cash<notional+fee:
            return self._transition(order,OrderStatus.CANCELLED,"Insufficient simulated cash at fill price.")
        fid=f"PF-{order.order_id}"
        fill=PaperFill(fid,order.order_id,order.quantity,fill_price,fee,fill_price-order.reference_price,self.clock())
        if fid in self.fills: raise ValueError("Duplicate fill identifier.")
        self.fills[fid]=fill; self.cash-=notional+fee
        self.positions[order.symbol]=PaperPosition(order.symbol,order.quantity,fill_price,fill_price,fee)
        return self._transition(order,OrderStatus.FILLED,"Deterministic market fill completed."),fill

    def mark_price(self,symbol,price):
        price=Decimal(str(price))
        if not price.is_finite() or price<=0: raise ValueError("Mark price must be finite and positive.")
        self.positions[symbol]=replace(self.positions[symbol],current_price=price)

    def close_position(self,symbol,price):
        position=self.positions[symbol]; price=Decimal(str(price)); now=self.clock()
        if not price.is_finite() or price<=0: raise ValueError("Close price must be finite and positive.")
        fill_price=(price*(Decimal("1")-self.slippage_bps/Decimal("10000"))).quantize(CENT)
        proceeds=position.quantity*fill_price; fee=(proceeds*self.fee_bps/Decimal("10000")).quantize(CENT)
        self.cash+=proceeds-fee
        pnl=(fill_price-position.average_entry_price)*position.quantity-position.entry_fees-fee
        trade=PaperTrade(f"PT-{next(self._ids):06d}",symbol,position.quantity,position.average_entry_price,fill_price,position.entry_fees+fee,pnl.quantize(CENT),now)
        self.trades.append(trade); del self.positions[symbol]
        for order in tuple(self.orders.values()):
            if order.symbol==symbol and order.status==OrderStatus.FILLED: self._transition(order,OrderStatus.CLOSED,"Position closed.")
        return trade

    def transition(self,order_id,status,reason): return self._transition(self.orders[order_id],status,reason)
    def _transition(self,order,status,reason,rejections=()):
        if status not in ALLOWED[order.status]: raise ValueError(f"Invalid order transition: {order.status} -> {status}")
        updated=replace(order,status=status,rejection_reasons=rejections or order.rejection_reasons)
        self.orders[order.order_id]=updated
        self.transitions.append(OrderTransition(order.order_id,order.status,status,self.clock(),reason))
        return updated
