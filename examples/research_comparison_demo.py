"""Compare deterministic baseline and candidate research metrics."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from models.research_provenance import ResearchMetricSet
from services.research_reproducibility import ResearchComparisonService
baseline=ResearchMetricSet("baseline",0.02,0.03,0.20,0.60); candidate=ResearchMetricSet("candidate",0.025,0.025,0.18,0.65)
print(ResearchComparisonService().compare(baseline,candidate)); print("No profitability claim; human review required.")

