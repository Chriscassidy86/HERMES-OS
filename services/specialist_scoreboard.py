"""Deterministic specialist scoring; produces recommendations and never mutations."""
from datetime import datetime,timezone
from models.specialist_scoreboard import SpecialistScore,SpecialistScoreboard

class SpecialistScoreboardService:
 NAMES=("Trend Specialist","Market Regime Specialist","Momentum Specialist","Volatility Specialist","Volume Specialist","Liquidity Specialist","Probability Specialist","Portfolio Context Specialist")
 def build(self,cards,*,as_of):
  if not isinstance(as_of,datetime) or as_of.tzinfo is None: raise ValueError("Scoreboard timestamp must be timezone-aware.")
  return SpecialistScoreboard(as_of.astimezone(timezone.utc).isoformat(),tuple(self._score(name,cards) for name in self.NAMES))
 def _score(self,name,cards):
  eligible=[]; neutral=excluded=0; symbols={}; regimes={}; timeframes={}; wins=[]; losses=[]
  for card in cards:
   calls={item[0]:item for item in card.entry_specialists}; call=calls.get(name)
   if not call: excluded+=1; continue
   direction=str(call[1]); confidence=float(call[2])
   if direction not in {"LONG","SHORT"}: neutral+=1; continue
   correct=name in card.correct_specialists; eligible.append((correct,confidence))
   self._group(symbols,card.symbol,correct); self._group(regimes,card.entry_regime,correct); self._group(timeframes,"4H",correct)
   (wins if card.net_pnl>0 else losses).append(correct)
  total=len(eligible); correct=sum(item[0] for item in eligible); incorrect=total-correct; weight=sum(item[1] for item in eligible)
  weighted=(sum(item[1] for item in eligible if item[0])/weight) if weight else None
  calibration=(1-sum(abs(item[1]/100-(1 if item[0] else 0)) for item in eligible)/total) if total else None
  streak=0
  for result,_ in reversed(eligible):
   if not result: break
   streak+=1
  last=max((card.exit_timestamp for card in cards),default=None)
  return SpecialistScore(name,total,correct,incorrect,neutral,excluded,self._ratio(correct,total),round(weighted,6) if weighted is not None else None,
   round(sum(x[1] for x in eligible)/total,6) if total else None,round(calibration,6) if calibration is not None else None,
   self._groups(symbols),self._groups(regimes),self._groups(timeframes),self._ratio(sum(wins),len(wins)),self._ratio(sum(losses),len(losses)),streak,
   "INSUFFICIENT SAMPLE: fewer than 20 eligible calls" if total<20 else None,last)
 @staticmethod
 def _group(target,key,correct):
  row=target.setdefault(key,[0,0]); row[0]+=1; row[1]+=int(correct)
 @staticmethod
 def _groups(values): return tuple((key,total,correct,round(correct/total,6)) for key,(total,correct) in sorted(values.items()))
 @staticmethod
 def _ratio(value,total): return round(value/total,6) if total else None
