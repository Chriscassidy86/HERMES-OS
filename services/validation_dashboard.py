"""Read-only searchable projection over persisted PAPER validation artifacts."""
from dataclasses import asdict
from datetime import datetime
from services.specialist_scoreboard import SpecialistScoreboardService

class ValidationDashboardService:
 ALLOWED=("symbol","timeframe","regime","recommendation","risk_result","date_from","date_to","result","specialist")
 def __init__(self,repository,clock): self.repository=repository; self.clock=clock
 def build(self,filters=None):
  filters=filters or {}
  unknown=set(filters)-set(self.ALLOWED)
  if unknown: raise ValueError(f"Unsupported validation filter: {sorted(unknown)[0]}")
  cards=self._filter_cards(self.repository.report_cards(500),filters); decisions=self._filter_decisions(self.repository.decision_quality(500),filters); summaries=self.repository.session_summaries(100)
  scoreboard=SpecialistScoreboardService().build(cards,as_of=self.clock())
  return {"filters":tuple(sorted(filters.items())),"specialists":tuple(asdict(x) for x in scoreboard.scores),"report_cards":tuple(asdict(x) for x in cards),
   "decisions":tuple(asdict(x) for x in decisions),"session_summaries":tuple(asdict(x) for x in summaries),"performance":self._performance(cards,decisions),"actions":()}
 def _filter_cards(self,cards,filters):
  result=[]
  for card in cards:
   if filters.get("symbol") and card.symbol!=filters["symbol"]: continue
   if filters.get("regime") and card.entry_regime!=filters["regime"]: continue
   if filters.get("recommendation") and card.entry_recommendation!=filters["recommendation"]: continue
   if filters.get("risk_result") and ("APPROVED" if card.risk_approved else "REJECTED")!=filters["risk_result"]: continue
   if filters.get("result") and ("WIN" if card.net_pnl>0 else "LOSS" if card.net_pnl<0 else "BREAK_EVEN")!=filters["result"]: continue
   if filters.get("specialist") and filters["specialist"] not in {x[0] for x in card.entry_specialists}: continue
   if not self._dates(card.exit_timestamp,filters): continue
   result.append(card)
  return tuple(result)
 def _filter_decisions(self,decisions,filters):
  result=[]
  for item in decisions:
   if filters.get("symbol") and item.symbol!=filters["symbol"]: continue
   if filters.get("regime") and item.regime!=filters["regime"]: continue
   if filters.get("recommendation") and item.recommendation!=filters["recommendation"]: continue
   if filters.get("risk_result") and item.risk_result!=filters["risk_result"]: continue
   if filters.get("specialist") and filters["specialist"] not in {x[0] for x in item.specialist_evidence}: continue
   if not self._dates(item.timestamp,filters): continue
   result.append(item)
  return tuple(result)
 @staticmethod
 def _dates(timestamp,filters):
  value=datetime.fromisoformat(timestamp)
  for key,operator in (("date_from",lambda a,b:a>=b),("date_to",lambda a,b:a<=b)):
   if filters.get(key):
    bound=datetime.fromisoformat(filters[key])
    if bound.tzinfo is None: raise ValueError("Date filters must include a timezone.")
    if not operator(value,bound): return False
  return True
 @staticmethod
 def _performance(cards,decisions):
  pnls=[x.net_pnl for x in cards]; waits=[x for x in decisions if x.recommendation in {"WAIT","HOLD"}]; rejected=[x for x in decisions if x.risk_result=="REJECTED"]
  return {"completed_trades":len(cards),"net_pnl":round(sum(pnls),8),"win_rate":round(sum(x>0 for x in pnls)/len(pnls),6) if pnls else None,
   "decision_count":len(decisions),"wait_hold_avoided":sum(x.wait_hold_avoided_bad_trade for x in waits),"wait_hold_missed_gain":sum(x.outcome_classification=="MISSED_GAIN" for x in waits),
   "risk_rejection_avoided":sum(x.outcome_classification=="REJECTION_AVOIDED_LOSS" for x in rejected),"risk_rejection_missed":sum(x.outcome_classification=="REJECTION_MISSED_GAIN" for x in rejected),
   "false_positive_rate":round(sum(x.outcome_classification=="FALSE_POSITIVE" for x in decisions)/len(decisions),6) if decisions else None,"limitation":"Limited PAPER validation does not prove profitability."}
