"""Deterministic outcome evaluation isolated from live decision creation."""
from datetime import datetime,timezone
from models.decision_quality import DecisionQualityRecord

class DecisionQualityService:
 LIMITATION="Outcome evaluation uses later PAPER observations and was not available to the original decision."
 def evaluate(self,cycle,checkpoints,*,horizon_seconds,position_open=False,execution_occurred=False,evaluated_at):
  if horizon_seconds<=0: raise ValueError("Evaluation horizon must be positive.")
  started=self._utc(cycle.get("timestamp")); evaluated=self._utc(evaluated_at)
  if int((evaluated-started).total_seconds())<horizon_seconds: raise ValueError("Evaluation horizon has not elapsed.")
  cutoff=started.timestamp()+horizon_seconds; rows=[]
  for item in checkpoints:
   timestamp=self._utc(item.get("timestamp")); price=float(item.get("price",0))
   if timestamp<=started: raise ValueError("No-look-ahead boundary requires later observations.")
   if timestamp.timestamp()>cutoff: continue
   if price<=0: raise ValueError("Checkpoint price is invalid.")
   rows.append((timestamp.isoformat(),price))
  if not rows: raise ValueError("Fresh later price checkpoints are required.")
  if max(self._utc(x[0]).timestamp() for x in rows)<cutoff-60: raise ValueError("Outcome checkpoints are stale for the requested horizon.")
  snapshot=cycle.get("snapshot") or {}; start=float(snapshot.get("price",0)); action=(cycle.get("recommendation") or {}).get("action","WAIT")
  moves=[(price-start)/start*100 for _,price in rows]; final=moves[-1]; approved=bool((cycle.get("risk_assessment") or {}).get("approved"))
  classification=self._classify(action,final,approved); rejected=None
  if not approved: rejected="WOULD_HAVE_GAINED" if ((action in {"BUY","LONG"} and final>0) or (action in {"SELL","SHORT"} and final<0)) else "WOULD_HAVE_LOST"
  evidence=tuple((item.get("source"),item.get("direction"),item.get("included")) for item in (cycle.get("evidence_summary") or {}).get("contributions",()))
  return DecisionQualityRecord(1,cycle.get("cycle_id","UNKNOWN"),snapshot.get("symbol","UNKNOWN"),started.isoformat(),snapshot.get("source","UNKNOWN"),start,
   snapshot.get("market_trend","UNKNOWN"),action,float((cycle.get("recommendation") or {}).get("confidence",0)),"APPROVED" if approved else "REJECTED",
   (cycle.get("risk_assessment") or {}).get("reason","No risk explanation."),evidence,bool(position_open),bool(execution_occurred),horizon_seconds,tuple(rows),classification,
   round(max(moves),6),round(min(moves),6),action in {"WAIT","HOLD"} and final<0,rejected,"PAPER_PUBLIC_OBSERVATION",self.LIMITATION,evaluated.isoformat())
 @staticmethod
 def _classify(action,move,approved):
  if action in {"WAIT","HOLD"}: return "AVOIDED_LOSS" if move<0 else ("MISSED_GAIN" if move>0 else "NEUTRAL")
  favorable=(action in {"BUY","LONG"} and move>0) or (action in {"SELL","SHORT"} and move<0)
  if not approved: return "REJECTION_MISSED_GAIN" if favorable else "REJECTION_AVOIDED_LOSS"
  return "GOOD_ENTRY" if favorable else "FALSE_POSITIVE"
 @staticmethod
 def _utc(value):
  if isinstance(value,str): value=datetime.fromisoformat(value)
  if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Decision-quality timestamps must be timezone-aware.")
  return value.astimezone(timezone.utc)
