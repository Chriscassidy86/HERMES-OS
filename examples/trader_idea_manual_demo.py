"""Trader Intelligence manual entry demo.

This example demonstrates manual entry of a single trader idea using the
TraderIdeaImporter. It uses an artificial fixture and is NOT real trading
advice.

Run from D:\\Desktop\\HERMES-OS:

    python examples/trader_idea_manual_demo.py
"""

from datetime import datetime, timezone

from services.trader_idea_importer import TraderIdeaImporter


def main() -> None:
    published = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    ingested = datetime(2025, 1, 15, 12, 5, tzinfo=timezone.utc)

    record = {
        "idea_id": "TI-MANUAL-001",
        "trader_id": "trader-fixture-001",
        "trader_display_name": "Fixture Trader Alpha",
        "source_id": "manual-source-001",
        "source_name": "Manual Operator Entry",
        "source_reference": "operator-notebook-2025-01-15",
        "published_at": published.isoformat(),
        "symbol": "BTC/USD",
        "timeframe": "4H",
        "market_regime": "BULL_TREND",
        "direction": "BULLISH",
        "stated_confidence": 0.75,
        "explanation": "Fixture thesis: moving averages are aligned upward with confirming volume.",
        "supporting_evidence": [
            "Short MA is above Long MA",
            "Volume is above average",
        ],
        "invalidation_conditions": [
            "Price closes below the short moving average",
        ],
        "assumptions": [
            "Public market data is accurate",
        ],
        "uncertainty": [
            "Historical patterns may not persist",
        ],
        "entry_zone_low": 95000.0,
        "entry_zone_high": 96000.0,
        "stop_loss": 92000.0,
        "target_prices": [105000.0, 110000.0],
        "suggested_action": "ENTER_LONG",
        "edited_after_publication": False,
        "ingestion_label": "MANUAL",
        "attribution": "Fixture Trader Alpha via manual operator entry",
        "warnings": [],
        "limitations": [
            "This is an artificial fixture, not real trading advice",
        ],
    }

    importer = TraderIdeaImporter()
    idea = importer.from_manual(record, ingested_at=ingested)

    print("=" * 60)
    print("TRADER INTELLIGENCE — MANUAL ENTRY DEMO")
    print("=" * 60)
    print(f"Idea ID:            {idea.idea_id}")
    print(f"Trader:             {idea.trader_display_name}")
    print(f"Symbol:             {idea.context.symbol}")
    print(f"Timeframe:          {idea.context.timeframe}")
    print(f"Market Regime:      {idea.context.market_regime}")
    print(f"Thesis Direction:   {idea.thesis.direction.value}")
    print(f"Stated Confidence:  {idea.thesis.stated_confidence}")
    print(f"Suggested Action:   {idea.suggested_action.value}")
    print(f"Published At:       {idea.published_at.isoformat()}")
    print(f"Source:             {idea.source_name}")
    print(f"Checksum:           {idea.checksum}")
    print(f"Evaluation Status:  {idea.evaluation_status.value}")
    print(f"Advisory Only:      True")
    print()
    print("NOTE: This is an artificial fixture, not real trading advice.")
    print("NOTE: Trader ideas are advisory evidence only and cannot execute trades.")
    print("=" * 60)


if __name__ == "__main__":
    main()
