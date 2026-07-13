"""Feed runtime PAPER results into an operator-started soak, if one exists."""
class WallClockSoakObserver:
 def __init__(self,service):
  self.service=service; state=service.load()
  if state is not None and state.completion_status=="RUNNING": service.recover()
 def observe(self,result):
  state=self.service.load()
  if state is None or state.completion_status!="RUNNING": return
  status=getattr(result,"status","")
  self.service.record(cycles=1,failovers=int(status=="PROVIDER_FAILURE"),errors=int(status.endswith("FAILURE")),alerts=int(status.endswith("FAILURE")))
