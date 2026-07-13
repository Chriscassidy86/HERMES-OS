"""Validated environment settings with a non-overridable paper-only boundary."""
from dataclasses import dataclass
from pathlib import Path
import os

def _positive_int(value,name):
    try: parsed=int(value)
    except (TypeError,ValueError) as exc: raise ValueError(f"{name} must be an integer.") from exc
    if parsed<=0: raise ValueError(f"{name} must be positive.")
    return parsed

@dataclass(frozen=True)
class RuntimeSettings:
    mode:str; database_path:Path; log_directory:Path; log_max_bytes:int; log_backup_count:int
    live_trading:bool=False
    @classmethod
    def from_env(cls,environ=None):
        env=os.environ if environ is None else environ; root=Path(__file__).resolve().parent.parent
        mode=env.get("HERMES_MODE","PAPER").upper()
        live=env.get("HERMES_LIVE_TRADING","false").lower() in {"1","true","yes","on"}
        if mode!="PAPER" or live: raise ValueError("Hermes OS release candidate supports PAPER mode only; live trading cannot be enabled.")
        return cls(mode,Path(env.get("HERMES_DATABASE",root/"data"/"hermes.sqlite3")),Path(env.get("HERMES_LOG_DIR",root/"logs")),
            _positive_int(env.get("HERMES_LOG_MAX_BYTES","5000000"),"HERMES_LOG_MAX_BYTES"),_positive_int(env.get("HERMES_LOG_BACKUP_COUNT","5"),"HERMES_LOG_BACKUP_COUNT"),False)
