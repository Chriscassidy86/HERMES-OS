"""Compose persisted paper state into an immutable presentation projection."""

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal

from models.web_dashboard import WebDashboardProjection


class WebDashboardService:
    """Read-only projection service. It cannot execute or mutate trading state."""

    SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD")
    PROVIDERS = ("Binance.US", "Coinbase", "Kraken")

    def __init__(self, command_center, version="V6 launch"):
        self.command_center = command_center
        self.version = version

    def build(self, *, learning_recommendations=(), recent_alerts=()):
        view = self.command_center.build(learning_recommendations=learning_recommendations)
        journal = self.command_center.journal
        healthy = view.database_health == "HEALTHY"
        cycles = tuple(journal.recent_cycles(100)) if healthy else ()
        portfolio = journal.current_portfolio() if healthy else None
        history = tuple(journal.portfolio_history(200)) if healthy else ()
        fills = tuple((portfolio or {}).get("fills", ()))
        orders = tuple((portfolio or {}).get("orders", ()))
        positions = self._positions(view.open_positions, cycles, fills, orders)
        trades = self._trades(view.closed_trades)
        latest = cycles[0] if cycles else None
        snapshot = (latest or {}).get("snapshot") or {}
        recommendation = (latest or {}).get("recommendation") or {}
        risk = (latest or {}).get("risk_assessment") or {}
        exposure = sum((Decimal(item["market_value"]) for item in positions), Decimal("0"))
        unrealized = sum((Decimal(item["unrealized_pnl"]) for item in positions), Decimal("0"))
        realized = sum((Decimal(item.get("realized_pnl", "0")) for item in trades), Decimal("0"))
        fees = sum((Decimal(item.get("fee", "0")) for item in fills), Decimal("0"))
        fees += sum((Decimal(item.get("fees", "0")) for item in trades), Decimal("0"))
        slippage = sum(
            (abs(Decimal(item.get("slippage", "0"))) * Decimal(item.get("quantity", "0")) for item in fills),
            Decimal("0"),
        )
        alerts = tuple(recent_alerts) or tuple(
            {"status": "WARNING", "message": item.get("reason", str(item))}
            for item in view.rejected_decisions[:20]
        )
        active_provider = snapshot.get("source", view.provider_health or "NOT_CONFIGURED")
        return WebDashboardProjection(
            view.banner, "PAPER", self.version,
            self.command_center.clock().astimezone(timezone.utc).isoformat(), 5,
            view.system_health, view.provider_health, view.database_health,
            active_provider, (latest or {}).get("timestamp"),
            recommendation.get("action", "WAIT"), float(recommendation.get("confidence", 0)),
            self._risk_status(latest), risk.get("reason", "No Risk Manager decision is available."),
            snapshot.get("market_trend", "UNKNOWN"), "10000.00", str(view.cash), str(view.equity),
            str(view.total_return), str(realized), str(unrealized), str(exposure), len(positions), len(trades),
            str(fees), str(slippage), str(view.drawdown), positions, trades,
            self._markets(cycles, positions), self._specialists(latest), self._mapping(view.decision_explanation),
            self._providers(cycles), tuple(self._cycle_row(item) for item in cycles[:20]),
            tuple(self._decision_row(item) for item in cycles[:20]), fills[-20:][::-1], trades[:20],
            alerts[:20], tuple(learning_recommendations), self._charts(cycles, history),
            tuple(view.disagreements) + tuple(view.exclusions) + tuple(view.notices), (),
        )

    @staticmethod
    def _mapping(value):
        if value is None:
            return None
        return asdict(value) if is_dataclass(value) else value

    @staticmethod
    def _risk_status(cycle):
        if not cycle:
            return "WAIT"
        status = cycle.get("final_status", "")
        risk = cycle.get("risk_assessment") or {}
        reasons = " ".join(cycle.get("rejection_reasons", ())).lower()
        if "stale" in reasons or "STALE" in status:
            return "DATA STALE"
        if "provider" in reasons or "PROVIDER" in status:
            return "PROVIDER FAILURE"
        if risk.get("approved"):
            return "APPROVED"
        action = (cycle.get("recommendation") or {}).get("action", "WAIT")
        return "WAIT" if action in {"WAIT", "HOLD"} else "REJECTED"

    def _positions(self, positions, cycles, fills, orders):
        order_by_id = {item.get("order_id"): item for item in orders}
        cycle_by_symbol = {}
        for cycle in cycles:
            symbol = (cycle.get("snapshot") or {}).get("symbol")
            cycle_by_symbol.setdefault(symbol, cycle)
        result = []
        for item in positions:
            symbol = item.get("symbol", "UNKNOWN")
            quantity = Decimal(item.get("quantity", "0"))
            entry = Decimal(item.get("average_entry_price", "0"))
            price = Decimal(item.get("current_price", "0"))
            entry_fees = Decimal(item.get("entry_fees", "0"))
            market_value = quantity * price
            pnl = (price - entry) * quantity - entry_fees
            matching = [fill for fill in fills if order_by_id.get(fill.get("order_id"), {}).get("symbol") == symbol]
            entry_time = matching[-1].get("timestamp") if matching else None
            snapshot = (cycle_by_symbol.get(symbol) or {}).get("snapshot") or {}
            result.append({
                "symbol": symbol, "quantity": str(quantity), "average_entry": str(entry),
                "current_price": str(price), "market_value": str(market_value), "unrealized_pnl": str(pnl),
                "unrealized_return": str((pnl / (entry * quantity) * 100) if entry * quantity else Decimal("0")),
                "position_age": self._age(entry_time), "provider": snapshot.get("source", "UNKNOWN"),
                "regime": snapshot.get("market_trend", "UNKNOWN"),
            })
        return tuple(result)

    @staticmethod
    def _trades(trades):
        result = []
        for item in trades:
            entry = Decimal(item.get("entry_price", "0"))
            pnl = Decimal(item.get("realized_pnl", "0"))
            quantity = Decimal(item.get("quantity", "0"))
            basis = entry * quantity
            result.append({
                "symbol": item.get("symbol", "UNKNOWN"), "entry_time": item.get("entry_time", "Unavailable"),
                "exit_time": item.get("closed_at"), "entry_price": str(entry),
                "exit_price": item.get("exit_price", "0"), "quantity": str(quantity),
                "fees": item.get("fees", "0"), "realized_pnl": str(pnl),
                "return": str((pnl / basis * 100) if basis else Decimal("0")),
                "trade_duration": item.get("duration", "Unavailable"),
                "result": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "FLAT"),
            })
        return tuple(result)

    def _markets(self, cycles, positions):
        latest = {}
        for cycle in cycles:
            symbol = (cycle.get("snapshot") or {}).get("symbol")
            if symbol and symbol not in latest:
                latest[symbol] = cycle
        position_by_symbol = {item["symbol"]: item for item in positions}
        rows = []
        for symbol in self.SYMBOLS:
            cycle = latest.get(symbol) or {}
            snapshot = cycle.get("snapshot") or {}
            recommendation = cycle.get("recommendation") or {}
            position = position_by_symbol.get(symbol)
            rows.append({
                "symbol": symbol, "price": snapshot.get("price"),
                "provider": snapshot.get("source", "NO OBSERVATION"),
                "regime": snapshot.get("market_trend", "UNKNOWN"),
                "recommendation": recommendation.get("action", "WAIT"),
                "confidence": recommendation.get("confidence", 0), "risk_status": self._risk_status(cycle),
                "last_cycle_time": cycle.get("timestamp"),
                "data_freshness": self._freshness(cycle.get("timestamp")),
                "position_open": position is not None,
                "unrealized_pnl": position.get("unrealized_pnl") if position else None,
            })
        return tuple(rows)

    def _age(self, timestamp):
        if not timestamp:
            return "Unavailable"
        entered = datetime.fromisoformat(timestamp)
        seconds = max(0, int((self.command_center.clock().astimezone(timezone.utc) - entered.astimezone(timezone.utc)).total_seconds()))
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        return f"{days}d {hours}h" if days else (f"{hours}h {minutes}m" if hours else f"{minutes}m")

    def _freshness(self, timestamp):
        if not timestamp:
            return "NO DATA"
        observed = datetime.fromisoformat(timestamp)
        age = self.command_center.clock().astimezone(timezone.utc) - observed.astimezone(timezone.utc)
        return "FRESH" if age.total_seconds() <= 300 else "DATA STALE"

    @staticmethod
    def _specialists(cycle):
        if not cycle:
            return ()
        reports = {item.get("agent_name"): item for item in cycle.get("specialist_reports", ())}
        contributions = {item.get("source"): item for item in (cycle.get("evidence_summary") or {}).get("contributions", ())}
        names = tuple(dict.fromkeys((*reports.keys(), *contributions.keys())))
        return tuple({
            "name": name,
            "conclusion": reports.get(name, {}).get("recommendation", contributions.get(name, {}).get("direction", "WAIT")),
            "confidence": reports.get(name, {}).get("confidence", contributions.get(name, {}).get("confidence", 0)),
            "weighted_score": contributions.get(name, {}).get("weighted_score"),
            "explanation": tuple(reports.get(name, {}).get("facts", ())),
            "included": contributions.get(name, {}).get("included", False),
            "exclusion_reason": contributions.get(name, {}).get("reason", "No weighted contribution is available."),
        } for name in names)

    def _providers(self, cycles):
        counts = {name: 0 for name in self.PROVIDERS}
        last = {name: None for name in self.PROVIDERS}
        for cycle in cycles:
            snapshot = cycle.get("snapshot") or {}
            source = snapshot.get("source")
            if source in counts:
                counts[source] += 1
                last[source] = last[source] or cycle.get("timestamp")
        return tuple({
            "name": name, "status": "HEALTHY" if counts[name] else "STANDBY / NO OBSERVATION",
            "priority": index + 1, "health_score": "100" if counts[name] else "N/A", "latency": "N/A",
            "success_count": counts[name], "failure_count": 0, "consecutive_failures": 0,
            "cooldown": "INACTIVE", "last_success": last[name], "last_failure": None,
        } for index, name in enumerate(self.PROVIDERS))

    @staticmethod
    def _cycle_row(cycle):
        snapshot = cycle.get("snapshot") or {}
        return {"cycle_id": cycle.get("cycle_id"), "timestamp": cycle.get("timestamp"),
                "symbol": snapshot.get("symbol"), "provider": snapshot.get("source"),
                "status": cycle.get("final_status")}

    def _decision_row(self, cycle):
        recommendation = cycle.get("recommendation") or {}
        return {"timestamp": cycle.get("timestamp"), "symbol": (cycle.get("snapshot") or {}).get("symbol"),
                "recommendation": recommendation.get("action", "WAIT"),
                "confidence": recommendation.get("confidence", 0), "risk_status": self._risk_status(cycle)}

    @staticmethod
    def _charts(cycles, history):
        portfolio = []
        peak = Decimal("0")
        for row in reversed(history):
            account = row.get("account") or {}
            positions = row.get("positions") or ()
            exposure = sum((Decimal(item.get("quantity", "0")) * Decimal(item.get("current_price", "0")) for item in positions), Decimal("0"))
            equity = Decimal(account.get("equity_balance", "0"))
            peak = max(peak, equity)
            drawdown = peak - equity
            portfolio.append({"timestamp": row.get("recorded_at"),
                              "equity": str(equity),
                              "cash": account.get("cash_balance", "0"),
                              "exposure": str(exposure), "drawdown": str(drawdown)})
        prices = [{"timestamp": item.get("timestamp"), "symbol": (item.get("snapshot") or {}).get("symbol"),
                   "value": (item.get("snapshot") or {}).get("price")} for item in reversed(cycles[:100])]
        decisions = [{"timestamp": item.get("timestamp"), "symbol": (item.get("snapshot") or {}).get("symbol"),
                      "value": {"SHORT": -1, "WAIT": 0, "HOLD": 0, "LONG": 1}.get((item.get("recommendation") or {}).get("action"), 0)}
                     for item in reversed(cycles[:100])]
        return {"portfolio": tuple(portfolio), "prices": tuple(prices),
                "recommendations": tuple(decisions),
                "disclaimer": "PAPER and public-observation history does not guarantee profitability."}
