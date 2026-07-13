"""Bounded recommendation-only learning after completed PAPER trades."""
from agents.learning import LearningExplanationEngine

class ContinuousLearningLoop:
    def __init__(self, *, history_limit=1000):
        if not 1 <= history_limit <= 10000: raise ValueError("Learning history limit is invalid.")
        self.history_limit=history_limit; self._outcomes=[]; self._ids=set()
    def record(self, outcome):
        if outcome.trade_id in self._ids: raise ValueError("Trade outcome already learned.")
        self._outcomes.append(outcome); self._ids.add(outcome.trade_id)
        while len(self._outcomes)>self.history_limit:
            removed=self._outcomes.pop(0); self._ids.remove(removed.trade_id)
        report=LearningExplanationEngine().explain(tuple(self._outcomes))
        if report.configuration_modified or not report.human_review_required: raise RuntimeError("Unsafe learning report.")
        return report
