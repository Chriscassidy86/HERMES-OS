"""Deterministic performance calculations over closed paper outcomes."""
from math import sqrt
from statistics import mean,pstdev
from models.performance import (DailyPerformanceReport,DrawdownReport,
 SpecialistScorecard,StrategyScorecard,WeeklyPerformanceReport,WinLossReport)

class PerformanceEngine:
    def strategy_scorecard(self,outcomes,starting_equity=10000.0):
        outcomes=tuple(outcomes); pnls=[o.pnl for o in outcomes]; gains=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
        equity=starting_equity; peak=equity; maximum=0.0
        for pnl in pnls:
            equity+=pnl; peak=max(peak,equity); maximum=max(maximum,peak-equity)
        expectancy=mean(pnls) if pnls else 0.0; gross_loss=abs(sum(losses))
        adjusted=(mean(pnls)/pstdev(pnls)*sqrt(len(pnls))) if len(pnls)>1 and pstdev(pnls)>0 else None
        return StrategyScorecard(len(pnls),len(gains),len(losses),round(len(gains)/len(pnls),4) if pnls else 0.0,
            round(len(losses)/len(pnls),4) if pnls else 0.0,round(expectancy,4),round(sum(gains)/gross_loss,4) if gross_loss else None,
            round(mean(gains),4) if gains else 0.0,round(mean(losses),4) if losses else 0.0,round(maximum,4),round(sum(pnls),4),round(adjusted,4) if adjusted is not None else None)
    def specialist_scorecards(self,outcomes):
        grouped={}
        for outcome in outcomes:
            for prediction in outcome.specialist_predictions: grouped.setdefault(prediction.source,[]).append((prediction,outcome.winning_direction))
        cards=[]
        for source,items in sorted(grouped.items()):
            correct=sum(p.direction==actual for p,actual in items); errors=[]
            for prediction,actual in items:
                probability=prediction.confidence/100.0; observed=1.0 if prediction.direction==actual else 0.0; errors.append((probability-observed)**2)
            cards.append(SpecialistScorecard(source,len(items),correct,round(correct/len(items),4),round(mean(errors),4)))
        return tuple(cards)
    def drawdown_report(self,outcomes,starting_equity=10000.0):
        score=self.strategy_scorecard(outcomes,starting_equity); return DrawdownReport(score.maximum_drawdown,round(starting_equity+score.total_pnl,4))
    def win_loss_report(self,outcomes):
        score=self.strategy_scorecard(outcomes); return WinLossReport(score.wins,score.losses,score.average_gain,score.average_loss,score.expectancy)
    def daily_report(self,date,outcomes): return DailyPerformanceReport(str(date),self.strategy_scorecard(outcomes),self.specialist_scorecards(outcomes))
    def weekly_report(self,week,outcomes): return WeeklyPerformanceReport(str(week),self.strategy_scorecard(outcomes),self.specialist_scorecards(outcomes))
