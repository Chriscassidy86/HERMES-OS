"""Read-only operator and CEO command-center application service."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from core.explanation import DecisionExplainer


@dataclass(frozen=True)
class CommandCenterView:
    banner: str
    system_health: str
    provider_health: str
    database_health: str
    latest_cycle: Any
    market_snapshot: Any
    market_regime: str
    specialists: tuple
    contributions: tuple
    agreements: tuple[str, ...]
    disagreements: tuple[str, ...]
    exclusions: tuple[str, ...]
    decision_explanation: Any
    executive_summary: str
    risk_decision: Any
    paper_execution_status: str
    cash: Decimal
    equity: Decimal
    open_positions: tuple
    closed_trades: tuple
    daily_pnl: Decimal
    weekly_pnl: Decimal
    total_return: Decimal
    drawdown: Decimal
    win_rate: Decimal
    profit_factor: Decimal | None
    rejected_decisions: tuple
    replay_status: str
    learning_recommendations: tuple
    notices: tuple[str, ...]
    actions: tuple = ()


class CommandCenterService:
    """Compose persisted state into an immutable view; never execute a trade."""

    def __init__(self, journal, provider=None, clock=None):
        self.journal = journal
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def build(self, *, replay_status="NOT_RUN", learning_recommendations=()):
        database_health = "HEALTHY"
        try:
            self.journal.validate_schema()
            cycles = self.journal.recent_cycles(20)
            portfolio = self.journal.current_portfolio()
            trades = tuple(self.journal.paper_trades(1000))
            rejections = tuple(self.journal.rejection_history(100))
        except Exception as exc:
            database_health = f"UNHEALTHY: {type(exc).__name__}"
            cycles, portfolio, trades, rejections = [], None, (), ()
        provider_health = getattr(self.provider, "health", None)
        provider_status = getattr(provider_health, "status", "NOT_CONFIGURED")
        provider_ok = bool(getattr(provider_health, "healthy", False)) if provider_health else True
        latest = cycles[0] if cycles else None
        evidence = latest.get("evidence_summary", {}) if latest else {}
        snapshot = latest.get("snapshot") if latest else None
        if self.provider is None and snapshot and snapshot.get("source"):
            provider_status = snapshot["source"]
        specialists = tuple(latest.get("specialist_reports", ())) if latest else ()
        contributions = tuple(evidence.get("contributions", ()))
        included = tuple(item for item in contributions if item.get("included"))
        directions = {item.get("direction") for item in included if item.get("direction") in {"LONG", "SHORT"}}
        agreements = tuple(sorted(directions)) if len(directions) == 1 else ()
        disagreements = tuple(evidence.get("conflicting_evidence", ()))
        exclusions = tuple(evidence.get("excluded_evidence", ()))
        explanation = DecisionExplainer().explain(latest) if latest else None
        executive_summary = explanation.executive_summary() if explanation else "No decision cycle is available."
        account = (portfolio or {}).get("account", {})
        cash = Decimal(account.get("cash_balance", "0")); equity = Decimal(account.get("equity_balance", "0"))
        pnls = [Decimal(item.get("realized_pnl", "0")) for item in trades]
        now = self.clock().astimezone(timezone.utc)
        daily = self._period_pnl(trades, now - timedelta(days=1)); weekly = self._period_pnl(trades, now - timedelta(days=7))
        gains = sum((p for p in pnls if p > 0), Decimal("0")); losses = abs(sum((p for p in pnls if p < 0), Decimal("0")))
        starting = Decimal("10000"); total = sum(pnls, Decimal("0")); peak = running = starting; drawdown = Decimal("0")
        for pnl in reversed(pnls):
            running += pnl; peak = max(peak, running); drawdown = max(drawdown, peak - running)
        notices = ("HUMAN APPROVAL REQUIRED FOR ALL CONFIGURATION CHANGES",) if learning_recommendations else ()
        healthy = database_health == "HEALTHY" and provider_ok
        return CommandCenterView(
            "PAPER MODE ONLY", "HEALTHY" if healthy else "UNHEALTHY", provider_status,
            database_health, latest, snapshot, (snapshot or {}).get("market_trend", "UNKNOWN"),
            specialists, contributions, agreements, disagreements, exclusions,
            explanation, executive_summary,
            latest.get("risk_assessment") if latest else None,
            latest.get("final_status", "NO_CYCLE") if latest else "NO_CYCLE",
            cash, equity, tuple((portfolio or {}).get("positions", ())), trades, daily, weekly,
            (total / starting * 100).quantize(Decimal("0.0001")), drawdown,
            (Decimal(sum(p > 0 for p in pnls)) / Decimal(len(pnls))).quantize(Decimal("0.0001")) if pnls else Decimal("0"),
            (gains / losses).quantize(Decimal("0.0001")) if losses else None,
            rejections, replay_status, tuple(learning_recommendations), notices,
        )

    @staticmethod
    def _period_pnl(trades, cutoff):
        total = Decimal("0")
        for item in trades:
            closed = datetime.fromisoformat(item["closed_at"])
            if closed.astimezone(timezone.utc) >= cutoff:
                total += Decimal(item.get("realized_pnl", "0"))
        return total
