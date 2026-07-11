"""Run a real, paper-only Hermes morning decision cycle."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from agents.trend.trend_specialist import TrendSpecialist
from core.decision_cycle import DecisionCycle
from reports.market_snapshot import MarketSnapshot


def main() -> None:
    snapshot = MarketSnapshot(
        symbol="BTC/USD",
        price=108_000.25,
        volume_24h=42_500_000_000,
        market_trend="Bullish",
        volatility=2.8,
        fear_greed_index=74,
    )
    result = DecisionCycle([TrendSpecialist()]).run(snapshot)

    print("=" * 58)
    print("HERMES PAPER-ONLY OPERATIONAL DECISION CYCLE")
    print("=" * 58)
    print(f"Cycle: {result.cycle_id}")
    print(f"Market: {result.snapshot.summary()}")
    for report in result.specialist_reports:
        print(f"Specialist: {report.summary()}")
    print(f"Evidence: {result.evidence_summary.summary()}")
    print(f"Recommendation: {result.recommendation.summary()}")
    print(f"Risk: {result.risk_assessment.summary()}")
    print(f"Final status: {result.final_status}")
    print(f"Paper execution eligible: {result.paper_execution_eligible}")
    print("Order placed: False")
    if result.rejection_reasons:
        print("Rejections:")
        for reason in result.rejection_reasons:
            print(f"- {reason}")
    print("=" * 58)


if __name__ == "__main__":
    main()
