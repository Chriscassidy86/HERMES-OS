"""Application-level paper session coordinator; synchronous and paper-only."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from core.decision_cycle import DecisionCycle
from database.journal import DuplicateCycleError
from data_providers.market_data import MarketDataError

@dataclass(frozen=True)
class PaperSessionResult:
    status: str; symbol: str; cycle_id: str|None; cycle: Any=None
    order: Any=None; fill: Any=None; errors: tuple[str,...]=()
    health: tuple[tuple[str,str],...]=()

class PaperTradingSession:
    def __init__(self,provider,portfolio,journal,clock,decision_cycle=None):
        self.provider=provider; self.portfolio=portfolio; self.journal=journal; self.clock=clock
        self.decision_cycle=decision_cycle or DecisionCycle(clock=clock)
    def run_cycle(self,symbol,timeframe="4H"):
        try: snapshot=self.provider.get_snapshot(symbol,timeframe)
        except Exception as exc:
            return self._result("PROVIDER_FAILURE",symbol,None,errors=(f"{type(exc).__name__}: {exc}",))
        try: cycle=self.decision_cycle.run(snapshot)
        except Exception as exc:
            return self._result("DECISION_FAILURE",symbol,None,errors=(f"{type(exc).__name__}: {exc}",))
        try: self.journal.save_cycle(cycle)
        except DuplicateCycleError:
            return self._result("DUPLICATE_CYCLE",symbol,cycle.cycle_id,cycle=cycle,errors=("Cycle already persisted; execution suppressed.",))
        except Exception as exc:
            return self._result("PERSISTENCE_FAILURE",symbol,cycle.cycle_id,cycle=cycle,errors=(f"{type(exc).__name__}: {exc}",))
        order=fill=None
        if cycle.paper_execution_eligible:
            try:
                order=self.portfolio.propose(cycle,snapshot.price)
                if order.status.value=="VALIDATED": order,fill=self.portfolio.execute_market(order.order_id)
            except Exception as exc:
                return self._result("PAPER_EXECUTION_FAILURE",symbol,cycle.cycle_id,cycle=cycle,order=order,errors=(f"{type(exc).__name__}: {exc}",))
        try: self.journal.save_portfolio(self.portfolio,cycle.cycle_id)
        except Exception as exc:
            return self._result("PERSISTENCE_FAILURE",symbol,cycle.cycle_id,cycle=cycle,order=order,fill=fill,errors=(f"{type(exc).__name__}: {exc}",))
        status="PAPER_FILLED" if fill else "NO_TRADE"
        return self._result(status,symbol,cycle.cycle_id,cycle=cycle,order=order,fill=fill)
    def _result(self,status,symbol,cycle_id,**values):
        health=(("session",status),("provider",getattr(self.provider.health,"status","UNKNOWN")),("paper_mode","ENFORCED"))
        return PaperSessionResult(status,symbol,cycle_id,health=health,**values)

class ScheduledPaperSession:
    """Explicit run-once schedule; callers control timing and no thread is started."""
    def __init__(self,session): self.session=session
    def run_once(self,symbols,timeframe="4H"):
        return tuple(self.session.run_cycle(symbol,timeframe) for symbol in symbols)
