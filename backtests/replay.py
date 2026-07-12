"""Deterministic historical replay with strict decision/future separation."""
from dataclasses import asdict,dataclass
from datetime import datetime
import csv,json
from pathlib import Path
from agents.performance.performance_engine import PerformanceEngine
from core.decision_cycle import DecisionCycle
from models.performance import SpecialistPrediction,TradeOutcome
from reports.market_snapshot import MarketSnapshot

@dataclass(frozen=True)
class HistoricalCandle:
    symbol:str; timestamp:datetime; close:float; volume:float; average_volume:float
    volatility:float; trend:str; previous_close:float; short_ma:float; long_ma:float; timeframe:str="4H"
class HistoricalCandleLoader:
    def load(self): raise NotImplementedError
class FixtureCandleLoader(HistoricalCandleLoader):
    def __init__(self,candles): self._candles=tuple(candles)
    def load(self): return self._candles
class ReplayClock:
    def __init__(self): self._current=None
    def set(self,value): self._current=value
    def now(self):
        if self._current is None: raise RuntimeError("Replay clock is not initialized.")
        return self._current
@dataclass(frozen=True)
class ReplayConfig:
    starting_balance:float=10000.0; fee_bps:float=10.0; slippage_bps:float=5.0; seed:int=0
@dataclass(frozen=True)
class ReplayResult:
    config:ReplayConfig; strategy:object; benchmark_return:float; outcomes:tuple
    decisions:tuple; equity_history:tuple; risk_rejections:int; no_trade_count:int
    metrics:object=None

@dataclass(frozen=True)
class ReplayMetrics:
    total_return:float; win_rate:float; loss_rate:float; maximum_drawdown:float
    profit_factor:float|None; expectancy:float; average_holding_seconds:float
    trade_count:int; risk_rejection_count:int; no_trade_count:int
    specialist_accuracy:tuple

class ReplaySession:
    def __init__(self,loader,config=ReplayConfig()): self.loader=loader; self.config=config; self.clock=ReplayClock()
    def run(self):
        candles=self.loader.load()
        if len(candles)<2: raise ValueError("Replay requires at least two candles.")
        decisions=[]; outcomes=[]; equity=self.config.starting_balance; history=[equity]; rejected=no_trade=0
        for index in range(len(candles)-1):
            current=candles[index]; self.clock.set(current.timestamp)
            snapshot=MarketSnapshot(current.symbol,current.close,current.volume,current.trend,current.volatility,50,current.previous_close,current.average_volume,current.short_ma,current.long_ma,current.timeframe,current.timestamp)
            decision=DecisionCycle(clock=self.clock.now).run(snapshot); decisions.append(decision)
            if not decision.risk_assessment.approved: rejected+=1
            if not decision.paper_execution_eligible or decision.recommendation.action!="LONG": no_trade+=1; history.append(equity); continue
            future_close=candles[index+1].close  # used only after the decision is complete
            notional=min(decision.risk_assessment.max_position_size,equity); quantity=notional/current.close
            entry=current.close*(1+self.config.slippage_bps/10000); exit_price=future_close*(1-self.config.slippage_bps/10000)
            fees=(entry+exit_price)*quantity*self.config.fee_bps/10000
            predictions=tuple(SpecialistPrediction(s.source,s.direction,s.confidence) for s in decision.decision_packet.signals)
            outcome=TradeOutcome(f"BT-{index+1:06d}",current.symbol,"LONG",entry,exit_price,quantity,fees,current.timestamp,candles[index+1].timestamp,predictions)
            outcomes.append(outcome); equity+=outcome.pnl; history.append(equity)
        strategy=PerformanceEngine().strategy_scorecard(outcomes,self.config.starting_balance)
        benchmark=round((candles[-1].close/candles[0].close-1)*100,4)
        holding=sum((item.closed_at-item.opened_at).total_seconds() for item in outcomes)/len(outcomes) if outcomes else 0.0
        specialist=PerformanceEngine().specialist_scorecards(outcomes)
        metrics=ReplayMetrics(round(strategy.total_pnl/self.config.starting_balance*100,4),strategy.win_rate,strategy.loss_rate,
            strategy.maximum_drawdown,strategy.profit_factor,strategy.expectancy,round(holding,2),strategy.sample_size,rejected,no_trade,specialist)
        return ReplayResult(self.config,strategy,benchmark,tuple(outcomes),tuple(decisions),tuple(round(v,4) for v in history),rejected,no_trade,metrics)
    @staticmethod
    def export(result,directory):
        directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
        (directory/"decisions.json").write_text(json.dumps([asdict(d) for d in result.decisions],default=str,sort_keys=True),encoding="utf-8")
        with (directory/"trades.csv").open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=("trade_id","symbol","direction","entry_price","exit_price","quantity","fees","pnl")); writer.writeheader()
            for trade in result.outcomes: writer.writerow({"trade_id":trade.trade_id,"symbol":trade.symbol,"direction":trade.direction,"entry_price":trade.entry_price,"exit_price":trade.exit_price,"quantity":trade.quantity,"fees":trade.fees,"pnl":trade.pnl})
