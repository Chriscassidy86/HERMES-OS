"""Execute one deterministic simulated market order; no exchange is contacted."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.decision_cycle import DecisionCycle
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot

now=datetime.now(timezone.utc)
snapshot=MarketSnapshot("BTC/USD",108000,42_500_000_000,"Bullish",2.8,74,
    106000,35_000_000_000,107500,104000,"4H",now)
result=DecisionCycle(clock=lambda:now).run(snapshot)
portfolio=PaperPortfolio(starting_cash=Decimal("10000"),clock=lambda:now)
order=portfolio.propose(result,Decimal("108000"))
order,fill=portfolio.execute_market(order.order_id)
print("PAPER MODE ONLY")
print("Cycle:",result.cycle_id)
print("Order:",order.order_id,order.status.value)
print("Fill:",fill.quantity,"@",fill.price,"fee",fill.fee)
print("Cash:",portfolio.account().cash_balance,"Equity:",portfolio.account().equity_balance)
print("Exchange contacted: False")
