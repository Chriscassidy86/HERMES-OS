"""Immutable per-symbol public-provider health state."""
from dataclasses import dataclass

@dataclass(frozen=True)
class RedundantProviderState:
    provider:str; symbol:str; successes:int; failures:int
    consecutive_failures:int; latency_ms:float; cooldown_remaining:int
    healthy:bool; score:float

@dataclass(frozen=True)
class AttributedPublicCandle:
    candle:object; source:str; states:tuple[RedundantProviderState,...]
    failover_count:int; public_only:bool=True
