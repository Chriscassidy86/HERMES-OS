"""Reproducible accelerated PAPER soak tooling with bounded state."""
from collections import deque
from dataclasses import asdict
from core.research.provenance import stable_checksum,stable_json
from models.soak_validation import SoakReport,SoakThresholds

class AcceleratedSoakHarness:
    def run(self,*,hours,symbols,interval_seconds=3600,thresholds=SoakThresholds(),injector=None,interrupt_after=None,database_size=0,log_size=0):
        if hours not in {24,72,168} or not symbols or interval_seconds<=0: raise ValueError("Soak configuration is invalid.")
        planned=hours*3600//interval_seconds*len(symbols); history=deque(maxlen=thresholds.maximum_history); counts={key:0 for key in ("success","failed","skipped","failover","stale","risk","orders","fills","trades","restart","recovery","circuit","alerts","dashboard","learning")}; durations=[]; per={symbol:0 for symbol in symbols}; peak_queue=0; interrupted=False
        for index in range(planned):
            if interrupt_after is not None and index>=interrupt_after: interrupted=True; break
            symbol=symbols[index%len(symbols)]; event=(injector(index,symbol) if injector else {}) or {}; per[symbol]+=1
            status=event.get("status","success"); counts[status if status in {"success","failed","skipped"} else "failed"]+=1
            for key in counts:
                if key not in {"success","failed","skipped"}: counts[key]+=int(bool(event.get(key,False)))
            duration=float(event.get("duration_ms",1)); durations.append(duration); queue=int(event.get("queue_depth",0)); peak_queue=max(peak_queue,queue); history.append((index,symbol,status))
        memory=len(history)*128; peak_memory=memory; total=sum(per.values()); rate=counts["failed"]/total if total else 0; failures=[]
        if rate>thresholds.maximum_failure_rate: failures.append("Failure rate exceeded threshold.")
        if peak_memory>thresholds.maximum_memory_bytes: failures.append("Memory ceiling exceeded.")
        if peak_queue>thresholds.maximum_queue_depth: failures.append("Queue depth exceeded threshold.")
        manifest={"hours":hours,"symbols":tuple(symbols),"interval_seconds":interval_seconds,"total_cycles":total,"counts":counts,"interrupted":interrupted,"paper_only":True}
        payload=stable_json(manifest); checksum=stable_checksum(manifest)
        return SoakReport(hours,total,tuple(sorted(per.items())),counts["success"],counts["failed"],counts["skipped"],counts["failover"],counts["stale"],counts["risk"],counts["orders"],counts["fills"],counts["trades"],counts["restart"],counts["recovery"],counts["circuit"],memory,peak_memory,round(sum(durations)/len(durations),6) if durations else 0,max(durations,default=0),peak_queue,database_size,log_size,counts["alerts"],counts["dashboard"],counts["learning"],interrupted,not failures,tuple(failures),payload,checksum)
    @staticmethod
    def export(report): return stable_json(asdict(report))
