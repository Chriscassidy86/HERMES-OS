"""Startup, health, and graceful shutdown primitives."""
from dataclasses import dataclass
from threading import Event

@dataclass(frozen=True)
class HealthCheck:
    name:str; healthy:bool; detail:str
@dataclass(frozen=True)
class HealthSummary:
    healthy:bool; checks:tuple[HealthCheck,...]

class StartupChecks:
    def __init__(self,settings,journal=None,provider=None): self.settings=settings; self.journal=journal; self.provider=provider
    def run(self):
        checks=[HealthCheck("paper_mode",self.settings.mode=="PAPER" and not self.settings.live_trading,"PAPER mode enforced")]
        try:
            self.settings.database_path.parent.mkdir(parents=True,exist_ok=True); self.settings.log_directory.mkdir(parents=True,exist_ok=True)
            checks.append(HealthCheck("directories",True,"Data and log directories writable"))
        except OSError as exc: checks.append(HealthCheck("directories",False,str(exc)))
        if self.journal:
            try: self.journal.validate_schema(); checks.append(HealthCheck("database",True,"Schema valid"))
            except Exception as exc: checks.append(HealthCheck("database",False,str(exc)))
        if self.provider:
            health=self.provider.health; checks.append(HealthCheck("provider",health.healthy,health.status))
        return HealthSummary(all(item.healthy for item in checks),tuple(checks))

class GracefulShutdown:
    def __init__(self): self._event=Event()
    def request(self,*_): self._event.set()
    @property
    def requested(self): return self._event.is_set()
