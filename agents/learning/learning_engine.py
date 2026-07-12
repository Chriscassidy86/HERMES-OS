"""Recommendation-only learning engine; never mutates production configuration."""
from models.performance import ProposedConfigurationPatch

class LearningEngine:
    def recommend_weight_change(self,scorecard,current_weight,min_samples=5):
        if scorecard.sample_size<min_samples: raise ValueError("Insufficient samples for a learning recommendation.")
        delta=0.1 if scorecard.accuracy>=0.65 else (-0.1 if scorecard.accuracy<0.45 else 0.0)
        proposed=round(max(0.1,min(2.0,current_weight+delta)),2)
        confidence=round(min(scorecard.sample_size/30.0,1.0)*max(scorecard.accuracy,1-scorecard.accuracy),4)
        return ProposedConfigurationPatch(
            affected_rule=f"specialist_weights.{scorecard.source}",current_value=current_weight,proposed_value=proposed,
            evidence=f"Accuracy {scorecard.accuracy:.2%}; Brier score {scorecard.brier_score:.4f}.",sample_size=scorecard.sample_size,
            before_estimate=scorecard.accuracy,after_estimate=round(min(1.0,scorecard.accuracy+0.02) if delta>0 else scorecard.accuracy,4),
            confidence=confidence,risks=("Historical performance may not persist.","Weight changes can amplify correlated evidence."),human_approval_required=True)
