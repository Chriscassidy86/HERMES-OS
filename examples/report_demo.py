from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from reports.agent_report import AgentReport


report = AgentReport(
    agent_name="Trend Agent",
    status="BULLISH",
    confidence=87.5,
    facts=[
        "Price above EMA200",
        "EMA20 above EMA50",
        "Higher highs detected",
    ],
    warnings=[
        "Volume slightly below average",
    ],
    recommendation="TREND_FOLLOWING_ALLOWED",
)

print(report.summary())
print("Valid:", report.is_valid())
print("Facts:", report.facts)
print("Warnings:", report.warnings)
