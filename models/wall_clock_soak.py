"""Persistent state for an operator-observed wall-clock PAPER soak."""
from dataclasses import dataclass,replace
@dataclass(frozen=True)
class WallClockSoakState:
 schema_version:int; session_id:str; mode:str; started_at:str; target_seconds:int; current_duration_seconds:int; uptime_seconds:int; restart_count:int
 cycle_count:int; provider_failover_count:int; database_size_bytes:int; log_size_bytes:int; process_rss_bytes:int|None; slow_cycle_count:int; error_count:int; alert_count:int
 stop_reason:str|None; completion_status:str; artifact_path:str|None
