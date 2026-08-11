"""Foreground paper-mode supervisor. It performs health checks, not trades."""
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from collections.abc import Iterable
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.health import GracefulShutdown, StartupChecks
from core.settings import RuntimeSettings
from data_providers.market_data import FixtureMarketDataProvider, ProviderHealth, SnapshotBuilder
from data_providers.public_adapters import (
    BinanceUSPublicAdapter,
    CoinbasePublicAdapter,
    KrakenPublicAdapter,
    PublicProviderGroup,
)
from database.journal import SQLiteAuditJournal
from paper_trading.portfolio import PaperPortfolio
from services.paper_operations import PaperOperationConfig, PaperOperationsService
from services.paper_session import PaperTradingSession

DEFAULT_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD")
PUBLIC_ADAPTERS = {
    "binanceus": BinanceUSPublicAdapter,
    "coinbase": CoinbasePublicAdapter,
    "kraken": KrakenPublicAdapter,
}


def _parse_symbols(value):
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_optional_int(value, name):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive.")
    return parsed


def _parse_non_negative_float(value, name):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not isfinite(parsed) or parsed < 0:
        raise ValueError(f"{name} must be finite and non-negative.")
    return parsed


def _load_fixture_provider(path, clock):
    with open(path, encoding="utf-8") as handle:
        fixtures = __import__("json").load(handle)
    return FixtureMarketDataProvider(fixtures, SnapshotBuilder(clock))


def _market_trend(close, previous):
    if close > previous:
        return "Bullish"
    if close < previous:
        return "Bearish"
    return "Sideways"


class PublicCandleMarketDataProvider:
    """Read-only public candle adapter that exposes the MarketDataProvider API."""

    def __init__(self, provider_group, builder):
        self.provider_group = provider_group
        self.builder = builder
        self.health = (
            provider_group.providers[0].health
            if provider_group.providers
            else ProviderHealth(False, "UNAVAILABLE", 0, "No public providers configured.")
        )

    def get_snapshot(self, symbol, timeframe="4H"):
        candle = self.provider_group.get_candle(symbol, timeframe)
        previous_price = candle.close
        data = {
            "symbol": candle.symbol,
            "price": candle.close,
            "volume_24h": candle.volume or 1.0,
            "market_trend": _market_trend(candle.close, previous_price),
            "volatility": 0.1,
            "fear_greed_index": 50,
            "timestamp": candle.timestamp,
            "previous_price": previous_price,
            "average_volume": candle.volume or 1.0,
            "short_moving_average": candle.close,
            "long_moving_average": candle.close,
        }
        snapshot = self.builder.build(data, timeframe)
        self.health = self.provider_group.providers[0].health
        for provider in self.provider_group.providers:
            if provider.name == candle.provider:
                self.health = provider.health
                break
        return snapshot


def _parse_public_adapters(value):
    names = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    if not names:
        raise ValueError("HERMES_PAPER_PUBLIC_PROVIDERS must include at least one provider.")
    unknown = tuple(name for name in names if name not in PUBLIC_ADAPTERS)
    if unknown:
        raise ValueError(f"Unknown public provider(s): {', '.join(unknown)}.")
    return names


def _print_batch(timestamp, results):
    statuses = ", ".join(f"{item.symbol}:{item.status}" for item in results)
    print(f"{timestamp.isoformat()} {statuses}", flush=True)


def _load_public_provider(env, clock):
    names = _parse_public_adapters(env.get("HERMES_PAPER_PUBLIC_PROVIDERS", "binanceus,coinbase,kraken"))
    timeout = _parse_non_negative_float(env.get("HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS", "5"), "HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS")
    retries = int(env.get("HERMES_PAPER_PUBLIC_RETRIES", "2"))
    if timeout <= 0:
        raise ValueError("HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS must be positive.")
    if retries < 0:
        raise ValueError("HERMES_PAPER_PUBLIC_RETRIES must be non-negative.")
    adapters = tuple(PUBLIC_ADAPTERS[name](clock=clock, timeout=timeout, retries=retries) for name in names)
    return PublicCandleMarketDataProvider(PublicProviderGroup(adapters), SnapshotBuilder(clock))


def _load_market_provider(env, clock):
    fixture_path = env.get("HERMES_PAPER_FIXTURES")
    source = env.get("HERMES_PAPER_DATA_SOURCE", "fixture" if fixture_path else "public").strip().lower()
    if source == "fixture":
        if not fixture_path:
            raise ValueError("HERMES_PAPER_FIXTURES is required when HERMES_PAPER_DATA_SOURCE=fixture.")
        return _load_fixture_provider(fixture_path, clock), "fixture"
    if source == "public":
        if fixture_path:
            raise ValueError("Set either HERMES_PAPER_DATA_SOURCE=fixture with fixtures or HERMES_PAPER_DATA_SOURCE=public without fixtures, not both.")
        return _load_public_provider(env, clock), "public"
    raise ValueError("HERMES_PAPER_DATA_SOURCE must be fixture or public.")


def _load_operation_config(env):
    symbols = _parse_symbols(env.get("HERMES_PAPER_SYMBOLS", ",".join(DEFAULT_SYMBOLS)))
    timeframe = env.get("HERMES_PAPER_TIMEFRAME", "4H")
    interval_seconds = _parse_non_negative_float(env.get("HERMES_PAPER_INTERVAL_SECONDS", "30"), "HERMES_PAPER_INTERVAL_SECONDS")
    max_failures = int(env.get("HERMES_PAPER_MAX_FAILURES", "3"))
    recent_cycle_limit = int(env.get("HERMES_PAPER_RECENT_CYCLE_LIMIT", "100"))
    if not timeframe.strip():
        raise ValueError("HERMES_PAPER_TIMEFRAME must be non-empty.")
    if max_failures < 1:
        raise ValueError("HERMES_PAPER_MAX_FAILURES must be positive.")
    if recent_cycle_limit < 1:
        raise ValueError("HERMES_PAPER_RECENT_CYCLE_LIMIT must be positive.")
    return PaperOperationConfig(
        symbols=symbols,
        timeframe=timeframe,
        interval_seconds=interval_seconds,
        max_consecutive_failures=max_failures,
        recent_cycle_limit=recent_cycle_limit,
    )


def main(environ=None):
    env = os.environ if environ is None else environ
    settings = RuntimeSettings.from_env(env)
    journal = SQLiteAuditJournal(settings.database_path)
    journal.initialize()
    clock = lambda: datetime.now(timezone.utc)
    try:
        provider, source = _load_market_provider(env, clock)
        config = _load_operation_config(env)
    except ValueError as exc:
        print(str(exc), flush=True)
        return 2
    startup = StartupChecks(settings, journal, provider).run()
    if not startup.healthy:
        for check in startup.checks:
            print(f"{check.name}: {check.healthy} {check.detail}", flush=True)
        return 1
    shutdown = GracefulShutdown()
    shutdown.install_signal_handlers()
    session = PaperTradingSession(provider, PaperPortfolio(clock=clock), journal, clock)
    operations = PaperOperationsService(session, journal, shutdown, clock=clock, on_batch=_print_batch)
    print(f"HERMES PAPER MODE SERVICE STARTED data_source={source}", flush=True)
    summary = operations.run(config, maximum_batches=_parse_optional_int(env.get("HERMES_PAPER_MAX_BATCHES"), "HERMES_PAPER_MAX_BATCHES"))
    print(f"HERMES PAPER MODE SERVICE STOPPED {summary.stopped_reason}", flush=True)
    print(f"BATCHES {summary.batches_completed} STATUSES {dict(summary.status_counts)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
