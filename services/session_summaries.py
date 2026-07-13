"""Deterministic aggregation of persisted PAPER validation artifacts."""
from datetime import datetime,timezone
from models.session_summary import PaperSessionSummary
class SessionSummaryService:
 PERIODS={"hourly":3600,"daily":86400,"weekly":604800}
 def build(self,period,started_at,ended_at,*,starting_equity,ending_equity,cards=(),decisions=(),fills=0,alerts=(),learning_recommendations=(),scoreboard=None):
  if period not in self.PERIODS: raise ValueError("Session summary period is invalid.")
  start=self._utc(started_at); end=self._utc(ended_at)
  if end<=start or int((end-start).total_seconds())!=self.PERIODS[period]: raise ValueError("Session summary UTC boundary is invalid.")
  pnls=[float(x.net_pnl) for x in cards]; gains=sum(x for x in pnls if x>0); losses=abs(sum(x for x in pnls if x<0)); by_symbol={}; by_regime={}
  for card,pnl in zip(cards,pnls): by_symbol[card.symbol]=by_symbol.get(card.symbol,0)+pnl; by_regime[card.entry_regime]=by_regime.get(card.entry_regime,0)+pnl
  actions=[x.recommendation for x in decisions]; approvals=sum(x.risk_result=="APPROVED" for x in decisions)
  strongest=weakest=None
  if scoreboard and scoreboard.scores:
   ranked=[x for x in scoreboard.scores if x.accuracy is not None]
   if ranked: strongest=max(ranked,key=lambda x:(x.accuracy,x.specialist)).specialist; weakest=min(ranked,key=lambda x:(x.accuracy,x.specialist)).specialist
  return PaperSessionSummary(1,f"{period}-{start.isoformat()}",period,start.isoformat(),end.isoformat(),float(starting_equity),float(ending_equity),round(sum(pnls),8),round(float(ending_equity)-float(starting_equity)-sum(pnls),8),
   round(sum(float(x.fees) for x in cards),8),round(sum(float(x.slippage) for x in cards),8),len(decisions),sum(x in {"BUY","LONG"} for x in actions),sum(x in {"SELL","SHORT"} for x in actions),actions.count("HOLD"),actions.count("WAIT"),approvals,len(decisions)-approvals,int(fills),len(cards),sum(x>0 for x in pnls),sum(x<0 for x in pnls),sum(x==0 for x in pnls),
   round(sum(x>0 for x in pnls)/len(pnls),6) if pnls else None,round(sum(pnls)/len(pnls),8) if pnls else None,round(gains/losses,6) if losses else None,self._drawdown(pnls),
   self._extreme(by_symbol,True),self._extreme(by_symbol,False),self._extreme(by_regime,True),self._extreme(by_regime,False),strongest,weakest,
   sum(x.outcome_classification=="PROVIDER_FAILURE" for x in decisions),sum("STALE" in x.outcome_classification for x in decisions),tuple(alerts),tuple(learning_recommendations),("Limited PAPER samples do not prove profitability.","Metrics are descriptive and do not mutate strategy, weights, or risk limits."))
 @staticmethod
 def _drawdown(pnls):
  peak=running=0; result=0
  for pnl in pnls: running+=pnl; peak=max(peak,running); result=max(result,peak-running)
  return round(result,8)
 @staticmethod
 def _extreme(values,best): return (max if best else min)(values,key=lambda x:(values[x],x)) if values else None
 @staticmethod
 def _utc(value):
  if isinstance(value,str): value=datetime.fromisoformat(value)
  if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Session timestamps must be timezone-aware.")
  return value.astimezone(timezone.utc)
