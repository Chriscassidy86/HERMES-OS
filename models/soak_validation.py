"""Immutable accelerated soak validation records."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SoakThresholds:
    maximum_failure_rate:float=.1; maximum_memory_bytes:int=10_000_000
    maximum_queue_depth:int=100; maximum_history:int=1000

@dataclass(frozen=True)
class SoakReport:
    duration_hours:int; total_cycles:int; cycles_per_symbol:tuple[tuple[str,int],...]
    successful_cycles:int; failed_cycles:int; skipped_cycles:int
    provider_failovers:int; stale_rejections:int; risk_rejections:int
    paper_orders:int; fills:int; closed_trades:int; restart_events:int
    recovery_events:int; circuit_breaker_events:int; memory_bytes:int
    peak_memory_bytes:int; average_cycle_ms:float; slowest_cycle_ms:float
    peak_queue_depth:int; database_size:int; log_size:int; alert_count:int
    dashboard_projections:int; learning_loops:int; interrupted:bool
    passed:bool; failures:tuple[str,...]; manifest_json:str; checksum:str
    accelerated_not_wall_clock:bool=True; paper_only:bool=True
