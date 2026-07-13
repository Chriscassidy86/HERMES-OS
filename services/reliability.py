"""Accelerated long-duration validation over the continuous PAPER engine."""
from dataclasses import dataclass
from math import ceil,isfinite
from services.paper_operations import PaperOperationConfig

@dataclass(frozen=True)
class ReliabilityReport:
    projected_hours:float; simulated_batches:int; stopped_reason:str
    bounded_memory:bool; paper_only:bool=True

class LongDurationReliabilityHarness:
    def __init__(self, operations): self.operations=operations
    def simulate(self, config:PaperOperationConfig, *, hours=24):
        if not isfinite(hours) or hours<=0 or config.interval_seconds<=0: raise ValueError("Reliability duration and interval must be positive.")
        batches=ceil(hours*3600/config.interval_seconds)
        summary=self.operations.run(config,maximum_batches=batches)
        return ReliabilityReport(hours,batches,summary.stopped_reason,int(dict(summary.cycle_metrics)["recent_cycles"])<=config.recent_cycle_limit)
