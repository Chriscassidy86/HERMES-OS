"""Fair deterministic scheduling over the existing PAPER session."""
from dataclasses import replace
from datetime import datetime,timezone
from math import isfinite
from models.multi_symbol import MultiSymbolRun,SymbolRuntimeState

class MultiSymbolScheduler:
    def __init__(self,session,journal,shutdown,*,clock,wait=None,history_limit=100,observer=None):
        if not 1<=history_limit<=10000: raise ValueError("History limit is invalid.")
        self.session=session; self.journal=journal; self.shutdown=shutdown; self.clock=clock
        self.wait=wait or shutdown.wait; self.history_limit=history_limit; self.observer=observer
    def run(self,schedules,*,timeframe="4H",interval_seconds=30,maximum_rounds=None):
        schedules=tuple(schedules)
        if not schedules or len({item.symbol for item in schedules})!=len(schedules): raise ValueError("Unique symbol schedules are required.")
        if not isfinite(interval_seconds) or interval_seconds<0: raise ValueError("Interval is invalid.")
        if maximum_rounds is not None and (isinstance(maximum_rounds,bool) or not isinstance(maximum_rounds,int) or maximum_rounds<1): raise ValueError("Maximum rounds must be a positive integer.")
        self.journal.validate_schema(); recovered=self.journal.restore_portfolio(self.session.portfolio)
        states={item.symbol:SymbolRuntimeState(item.symbol,item.enabled,"UNKNOWN",None,None,"UNKNOWN","UNKNOWN",0,0,0,()) for item in schedules}
        ordering=[]; rounds=0; reason="SHUTDOWN_REQUESTED"
        while not self.shutdown.requested:
            active=[item.symbol for item in schedules if item.enabled]
            if active:
                offset=rounds%len(active); active=active[offset:]+active[:offset]
            for symbol in active:
                now=self._now(); result=self.session.run_cycle(symbol,timeframe); ordering.append(symbol); old=states[symbol]
                if self.observer is not None: self.observer(result)
                failed=result.status.endswith("FAILURE")
                history=(old.history+((now,result.status),))[-self.history_limit:]
                cycle=result.cycle; regime=getattr(getattr(cycle,"snapshot",None),"market_trend",old.regime)
                mtf=str(getattr(getattr(cycle,"recommendation",None),"action",old.multi_timeframe))
                states[symbol]=replace(old,provider_health="FAILED" if result.status=="PROVIDER_FAILURE" else "HEALTHY",last_failure=now if failed else old.last_failure,last_success=old.last_success if failed else now,regime=regime,multi_timeframe=mtf,failed_cycles=old.failed_cycles+int(failed),successful_cycles=old.successful_cycles+int(not failed),history=history)
            for item in schedules:
                if not item.enabled:
                    old=states[item.symbol]; states[item.symbol]=replace(old,skipped_cycles=old.skipped_cycles+1)
            rounds+=1
            if maximum_rounds is not None and rounds>=maximum_rounds: reason="ROUND_LIMIT_REACHED"; break
            if self.wait(interval_seconds): break
        return MultiSymbolRun(rounds,tuple(states[key] for key in sorted(states)),tuple(ordering),recovered,reason)
    def _now(self):
        value=self.clock()
        if not isinstance(value,datetime) or value.tzinfo is None: raise ValueError("Scheduler clock must be timezone-aware.")
        return value.astimezone(timezone.utc)
