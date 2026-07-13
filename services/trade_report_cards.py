"""Deterministic report cards over completed, already-persisted PAPER trades."""

from dataclasses import asdict
from datetime import datetime, timezone
import json

from models.trade_report_card import TradeReportCard


class TradeReportCardService:
    LIMITATION = "Limited PAPER results do not prove profitability or future performance."

    def build(self, trade, entry_cycle, exit_cycle, *, slippage=0.0, exit_reason="PAPER position closed", learning_recommendations=()):
        entry_evidence = (entry_cycle or {}).get("evidence_summary") or {}
        entry_risk = (entry_cycle or {}).get("risk_assessment") or {}
        if not entry_evidence.get("contributions"):
            raise ValueError("Entry evidence is required for a trade report card.")
        if not entry_risk.get("approved"):
            raise ValueError("Risk Manager approval is required for a trade report card.")
        entry_time = self._utc((entry_cycle or {}).get("timestamp"))
        exit_time = self._utc(trade.get("closed_at") or (exit_cycle or {}).get("timestamp"))
        if exit_time < entry_time:
            raise ValueError("Trade exit cannot precede entry.")
        quantity = float(trade["quantity"]); entry_price = float(trade["entry_price"]); exit_price = float(trade["exit_price"])
        fees = float(trade.get("fees", 0)); slippage = float(slippage)
        gross = (exit_price - entry_price) * quantity; net = gross - fees - slippage
        recommendation = (entry_cycle.get("recommendation") or {}).get("action", "WAIT")
        confidence = float((entry_cycle.get("recommendation") or {}).get("confidence", 0))
        outcome_direction = "LONG" if net > 0 else ("SHORT" if net < 0 else "WAIT")
        correct, incorrect = self._score(entry_evidence["contributions"], outcome_direction)
        thesis = recommendation == outcome_direction or (recommendation in {"WAIT", "HOLD"} and net == 0)
        entry_snapshot = entry_cycle.get("snapshot") or {}; exit_snapshot = (exit_cycle or {}).get("snapshot") or {}
        return TradeReportCard(
            1, str(trade["trade_id"]), str(trade["symbol"]), entry_time.isoformat(), exit_time.isoformat(),
            entry_price, exit_price, quantity, round(gross, 8), round(net, 8), fees, slippage,
            round(net / (entry_price * quantity) * 100, 6) if entry_price * quantity else 0.0,
            int((exit_time - entry_time).total_seconds()), entry_snapshot.get("market_trend", "UNKNOWN"),
            exit_snapshot.get("market_trend", "UNKNOWN"), recommendation, confidence, True,
            entry_risk.get("reason", "Risk Manager approved the configured PAPER size."),
            self._specialists(entry_cycle), self._specialists(exit_cycle),
            tuple(item.get("reason", "") for item in entry_evidence["contributions"] if item.get("included")),
            tuple(entry_evidence.get("excluded_evidence", ())),
            ("Validated public observations are treated as supplied facts.", "Strategy, weights, and risk limits remain unchanged."),
            tuple(entry_evidence.get("conflicting_evidence", ())) or ("Future market outcomes remain uncertain.",),
            exit_reason, thesis, correct, incorrect, round(abs(confidence / 100 - (1.0 if thesis else 0.0)), 6),
            tuple(learning_recommendations), "PAPER ONLY",
            tuple(dict.fromkeys(filter(None, (entry_snapshot.get("source"), exit_snapshot.get("source"))))), self.LIMITATION,
        )

    @staticmethod
    def _utc(value):
        if isinstance(value, str): value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is None: raise ValueError("Report-card timestamps must be timezone-aware.")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _specialists(cycle):
        return tuple(sorted(((item.get("agent_name", "UNKNOWN"), item.get("recommendation", "WAIT"), float(item.get("confidence", 0))) for item in (cycle or {}).get("specialist_reports", ())), key=lambda item: item[0]))

    @staticmethod
    def _score(contributions, outcome):
        correct=[]; incorrect=[]
        for item in contributions:
            if not item.get("included") or item.get("direction") not in {"LONG", "SHORT"}: continue
            (correct if item.get("direction") == outcome else incorrect).append(item.get("source", "UNKNOWN"))
        return tuple(sorted(correct)), tuple(sorted(incorrect))

    @staticmethod
    def stable_json(card):
        return json.dumps(asdict(card), sort_keys=True, separators=(",", ":"))
