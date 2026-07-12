"""Foundation IV.3 paper portfolio lifecycle and accounting tests."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from core.decision_cycle import DecisionCycle
from paper_trading.models import OrderStatus
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot

NOW=datetime(2026,7,11,12,tzinfo=timezone.utc)
def eligible_cycle(at=NOW):
    snap=MarketSnapshot("BTC/USD",100.0,1500.0,"Bullish",2.0,55,
        98.0,1000.0,101.0,99.0,"4H",at)
    return DecisionCycle(clock=lambda:at).run(snap)
def portfolio(cash="10000",fee="10",slippage="5"):
    return PaperPortfolio(Decimal(cash),Decimal(fee),Decimal(slippage),lambda:NOW)

class PaperPortfolioTests(unittest.TestCase):
    def test_open_long_position(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); order,fill=book.execute_market(order.order_id)
        self.assertEqual(OrderStatus.FILLED,order.status); self.assertIn("BTC/USD",book.positions)
    def test_short_is_safely_rejected(self):
        snap=MarketSnapshot("BTC/USD",98,1500,"Bearish",2,55,100,1000,99,101,"4H",NOW)
        result=DecisionCycle(clock=lambda:NOW).run(snap); order=portfolio().propose(result,"98")
        self.assertEqual(OrderStatus.REJECTED,order.status)
    def test_insufficient_funds(self):
        book=portfolio("1"); order=book.propose(eligible_cycle(),"100")
        rejected=book.execute_market(order.order_id)
        self.assertEqual(OrderStatus.CANCELLED,rejected.status)
    def test_risk_denied_trade(self):
        snap=MarketSnapshot("BTC/USD",100,1000,"Sideways",2,55,timestamp=NOW)
        result=DecisionCycle(clock=lambda:NOW).run(snap); order=portfolio().propose(result,"100")
        self.assertEqual(OrderStatus.REJECTED,order.status)
    def test_fees_and_slippage(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); _,fill=book.execute_market(order.order_id)
        self.assertEqual(Decimal("100.05"),fill.price); self.assertEqual(Decimal("0.02"),fill.fee)
    def test_unrealized_pnl(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id)
        book.mark_price("BTC/USD","110"); self.assertGreater(book.positions["BTC/USD"].unrealized_pnl,0)
    def test_close_and_realized_pnl(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id)
        trade=book.close_position("BTC/USD","110")
        self.assertGreater(trade.realized_pnl,0); self.assertNotIn("BTC/USD",book.positions)
    def test_duplicate_fill_prevented(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id)
        with self.assertRaises(ValueError): book.execute_market(order.order_id)
        self.assertEqual(1,len(book.fills))
    def test_invalid_transition_prevented(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100")
        with self.assertRaises(ValueError): book.transition(order.order_id,OrderStatus.CLOSED,"invalid")
    def test_accounting_invariant(self):
        book=portfolio(); initial=book.account().equity_balance; order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id)
        account=book.account(); expected=book.cash+sum(p.market_value for p in book.positions.values())
        self.assertEqual(expected.quantize(Decimal("0.01")),account.equity_balance); self.assertLess(account.equity_balance,initial)
    def test_existing_position_rejected_without_mutation(self):
        book=portfolio(); first=book.propose(eligible_cycle(),"100"); book.execute_market(first.order_id)
        cash=book.cash; fills=dict(book.fills); second=book.propose(eligible_cycle(NOW+timedelta(minutes=1)),"101")
        self.assertEqual(OrderStatus.REJECTED,second.status); self.assertEqual(cash,book.cash); self.assertEqual(fills,book.fills)
    def test_order_ids_remain_unique_across_cycles(self):
        first=portfolio().propose(eligible_cycle(),"100"); second=portfolio().propose(eligible_cycle(NOW+timedelta(minutes=1)),"100")
        self.assertNotEqual(first.order_id,second.order_id)
    def test_invalid_close_price_does_not_mutate(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id); before=book.account()
        with self.assertRaises(ValueError): book.close_position("BTC/USD","-1")
        self.assertEqual(before,book.account()); self.assertIn("BTC/USD",book.positions)
    def test_non_finite_mark_price_does_not_mutate(self):
        book=portfolio(); order=book.propose(eligible_cycle(),"100"); book.execute_market(order.order_id); before=book.positions["BTC/USD"]
        for price in ("NaN","Infinity","-Infinity"):
            with self.assertRaises(ValueError): book.mark_price("BTC/USD",price)
            self.assertEqual(before,book.positions["BTC/USD"])
    def test_duplicate_cycle_order_does_not_overwrite(self):
        book=portfolio(); first=book.propose(eligible_cycle(),"100")
        with self.assertRaises(ValueError): book.propose(eligible_cycle(),"100")
        self.assertEqual(first,book.orders[first.order_id])
    def test_non_finite_and_zero_quantity_sizes_are_rejected(self):
        nan_order=portfolio().propose(eligible_cycle(),"NaN"); self.assertEqual(OrderStatus.REJECTED,nan_order.status)
        tiny=portfolio().propose(eligible_cycle(),"1000000000000",notional="0.01"); self.assertEqual(OrderStatus.REJECTED,tiny.status); self.assertEqual(Decimal("0"),tiny.quantity)
if __name__=="__main__": unittest.main()
