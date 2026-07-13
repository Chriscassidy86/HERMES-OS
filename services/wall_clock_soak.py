"""Safe local lifecycle for wall-clock PAPER soak validation."""
from dataclasses import asdict,replace
from datetime import datetime,timezone
import json,os
from models.wall_clock_soak import WallClockSoakState
class WallClockSoakService:
 TARGETS={"24h":86400,"72h":259200,"7d":604800}
 def __init__(self,state_path,*,clock=None,database_path=None,log_path=None,rss_provider=None): self.path=str(state_path); self.clock=clock or (lambda:datetime.now(timezone.utc)); self.database_path=database_path; self.log_path=log_path; self.rss_provider=rss_provider or self._rss
 def start(self,target):
  if target not in self.TARGETS: raise ValueError("Soak target must be 24h, 72h, or 7d.")
  existing=self.load()
  if existing and existing.completion_status=="RUNNING": raise ValueError("A PAPER soak is already running.")
  now=self._now(); state=WallClockSoakState(1,f"SOAK-{now:%Y%m%dT%H%M%SZ}","PAPER ONLY",now.isoformat(),self.TARGETS[target],0,0,0,0,0,self._size(self.database_path),self._size(self.log_path),self.rss_provider(),0,0,0,None,"RUNNING",None); self._save(state); return state
 def status(self):
  state=self.load()
  if not state: raise ValueError("No soak session exists.")
  elapsed=max(0,int((self._now()-datetime.fromisoformat(state.started_at)).total_seconds()))
  completion="COMPLETED" if state.completion_status=="RUNNING" and elapsed>=state.target_seconds else state.completion_status
  updated=replace(state,current_duration_seconds=elapsed,uptime_seconds=elapsed,database_size_bytes=self._size(self.database_path),log_size_bytes=self._size(self.log_path),process_rss_bytes=self.rss_provider(),completion_status=completion)
  self._save(updated); return updated
 def recover(self):
  state=self.status()
  if state.completion_status!="RUNNING": return state
  state=replace(state,restart_count=state.restart_count+1); self._save(state); return state
 def record(self,*,cycles=0,failovers=0,slow_cycles=0,errors=0,alerts=0):
  state=self.status()
  if state.completion_status!="RUNNING": raise ValueError("Soak is not running.")
  state=replace(state,cycle_count=state.cycle_count+cycles,provider_failover_count=state.provider_failover_count+failovers,slow_cycle_count=state.slow_cycle_count+slow_cycles,error_count=state.error_count+errors,alert_count=state.alert_count+alerts); self._save(state); return state
 def stop(self,reason="Operator requested safe stop"):
  state=self.status()
  if state.completion_status!="RUNNING": raise ValueError("Soak is not running.")
  state=replace(state,stop_reason=reason,completion_status="STOPPED"); self._save(state); return state
 def export(self,destination):
  state=self.status(); payload={"state":asdict(state),"limitation":"A completed PAPER soak does not prove profitability or live readiness."}; text=json.dumps(payload,sort_keys=True,separators=(",",":")); os.makedirs(os.path.dirname(str(destination)) or ".",exist_ok=True)
  with open(destination,"w",encoding="utf-8",newline="\n") as output: output.write(text+"\n")
  state=replace(state,artifact_path=str(destination)); self._save(state); return text
 def load(self):
  if not os.path.exists(self.path): return None
  with open(self.path,encoding="utf-8") as source: return WallClockSoakState(**json.load(source))
 def _save(self,state):
  os.makedirs(os.path.dirname(self.path) or ".",exist_ok=True)
  with open(self.path,"w",encoding="utf-8",newline="\n") as output: json.dump(asdict(state),output,sort_keys=True,separators=(",",":")); output.write("\n")
 def _now(self):
  value=self.clock()
  if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Soak clock must be timezone-aware.")
  return value.astimezone(timezone.utc)
 @staticmethod
 def _size(path):
  if not path or not os.path.exists(path): return 0
  if os.path.isdir(path): return sum(os.path.getsize(os.path.join(root,name)) for root,_,names in os.walk(path) for name in names)
  return os.path.getsize(path)
 @staticmethod
 def _rss():
  try:
   import resource
   return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
  except (ImportError,AttributeError,OSError): return None
