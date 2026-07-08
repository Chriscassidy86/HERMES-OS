from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from models.evidence_summary import EvidenceSummary
from core.briefing.executive_brief import ExecutiveBrief


summary = EvidenceSummary(
    symbol="BTC/USD",
    bullish=2,
    bearish=0,
    neutral=1,
    average_confidence=71.67,
    signal_count=3,
)

brief = ExecutiveBrief()

print(brief.create(summary))