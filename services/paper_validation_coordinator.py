"""Connect persisted PAPER facts to validation artifacts without influencing trading."""
from datetime import datetime,timedelta,timezone
from services.decision_quality import DecisionQualityService
from services.session_summaries import SessionSummaryService
from services.specialist_scoreboard import SpecialistScoreboardService
from services.trade_report_cards import TradeReportCardService

class PaperValidationCoordinator:
 HORIZON=3600
 def __init__(self,journal,repository,clock): self.journal=journal; self.repository=repository; self.clock=clock; self.errors=[]
 def observe(self,result):
  if getattr(result,"cycle",None) is not None:
   for operation in (self._decisions,self._report_cards,self._summaries):
    try: operation()
    except Exception as exc: self.errors=(self.errors+[f"{operation.__name__}: {type(exc).__name__}"])[-100:]
 def _decisions(self):
  cycles=tuple(reversed(self.journal.recent_cycles(1000))); existing={x.cycle_id for x in self.repository.decision_quality(1000)}
  for index,cycle in enumerate(cycles):
   if cycle.get("cycle_id") in existing: continue
   start=datetime.fromisoformat(cycle["timestamp"]); target=start+timedelta(seconds=self.HORIZON); later=None
   symbol=(cycle.get("snapshot") or {}).get("symbol")
   for candidate in cycles[index+1:]:
    stamp=datetime.fromisoformat(candidate["timestamp"])
    if (candidate.get("snapshot") or {}).get("symbol")==symbol and target<=stamp<=target+timedelta(seconds=60): later=candidate; break
   if later is None: continue
   record=DecisionQualityService().evaluate(cycle,({"timestamp":later["timestamp"],"price":later["snapshot"]["price"]},),horizon_seconds=self.HORIZON,position_open=False,execution_occurred=bool(cycle.get("paper_execution_eligible")),evaluated_at=later["timestamp"])
   try: self.repository.save_decision_quality(record)
   except ValueError: pass
 def _report_cards(self):
  existing={x.trade_id for x in self.repository.report_cards(1000)}; cycles=tuple(reversed(self.journal.recent_cycles(1000)))
  for trade in self.journal.paper_trades(1000):
   if trade.get("trade_id") in existing: continue
   closed=datetime.fromisoformat(trade["closed_at"]); symbol=trade.get("symbol")
   candidates=[x for x in cycles if (x.get("snapshot") or {}).get("symbol")==symbol and datetime.fromisoformat(x["timestamp"])<=closed]
   entries=[x for x in candidates if (x.get("risk_assessment") or {}).get("approved") and (x.get("evidence_summary") or {}).get("contributions")]
   if not entries or not candidates: continue
   card=TradeReportCardService().build(trade,entries[0],candidates[-1],exit_reason="Persisted PAPER position closed")
   try: self.repository.save_report_card(card)
   except ValueError: pass
 def _summaries(self):
  now=self._utc(self.clock()); decisions=self.repository.decision_quality(1000); cards=self.repository.report_cards(1000); portfolio=self.journal.current_portfolio() or {}; equity=float((portfolio.get("account") or {}).get("equity_balance",0)); scoreboard=SpecialistScoreboardService().build(cards,as_of=now)
  periods=(("hourly",timedelta(hours=1)),("daily",timedelta(days=1)),("weekly",timedelta(days=7)))
  for period,length in periods:
   end=now.replace(minute=0,second=0,microsecond=0) if period=="hourly" else now.replace(hour=0,minute=0,second=0,microsecond=0)
   if period=="weekly": end=end-timedelta(days=end.weekday())
   start=end-length; selected_decisions=tuple(x for x in decisions if start<=datetime.fromisoformat(x.timestamp)<end); selected_cards=tuple(x for x in cards if start<=datetime.fromisoformat(x.exit_timestamp)<end)
   summary=SessionSummaryService().build(period,start,end,starting_equity=equity,ending_equity=equity,cards=selected_cards,decisions=selected_decisions,scoreboard=scoreboard)
   try: self.repository.save_session_summary(summary)
   except ValueError: pass
 @staticmethod
 def _utc(value):
  if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Validation coordinator clock must be timezone-aware.")
  return value.astimezone(timezone.utc)
