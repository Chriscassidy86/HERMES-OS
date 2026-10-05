"""Foreground paper-mode supervisor.

The paper service performs validated public market-data collection,
deterministic feature calculation, decision processing, and paper-only
operations. It contains no live trading capability.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


from agents.market_intelligence.feature_pipeline import (  # noqa: E402
    MarketFeatures,
    build_market_features,
)
from core.health import GracefulShutdown, StartupChecks  # noqa: E402
from core.settings import RuntimeSettings  # noqa: E402
from data_providers.market_data import (  # noqa: E402
    FixtureMarketDataProvider,
    ProviderHealth,
    SnapshotBuilder,
)
from data_providers.public_adapters import (  # noqa: E402
    BinanceUSPublicAdapter,
    CoinbasePublicAdapter,
    KrakenPublicAdapter,
    PublicCandle,
    PublicProviderGroup,
)
from database.journal import SQLiteAuditJournal  # noqa: E402
from paper_trading.portfolio import PaperPortfolio  # noqa: E402
from reports.market_snapshot import MarketSnapshot  # noqa: E402
from services.paper_operations import (  # noqa: E402
    PaperOperationConfig,
    PaperOperationsService,
)
from services.paper_session import PaperTradingSession  # noqa: E402


DEFAULT_SYMBOLS = (
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XRP/USD",
)

PUBLIC_ADAPTERS = {
    "binanceus": BinanceUSPublicAdapter,
    "coinbase": CoinbasePublicAdapter,
    "kraken": KrakenPublicAdapter,
}

DEFAULT_HISTORICAL_CANDLES = 100
MAX_HISTORICAL_CANDLES = 200


def _parse_symbols(value):
    if value is None:
        raise ValueError("HERMES_PAPER_SYMBOLS cannot be empty.")

    symbols = tuple(
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    )

    if not symbols:
        raise ValueError("HERMES_PAPER_SYMBOLS must include at least one symbol.")

    return symbols


def _parse_optional_int(value, name):
    if value in (None, ""):
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be an integer."
        ) from exc

    if parsed <= 0:
        raise ValueError(
            f"{name} must be positive."
        )

    return parsed


def _parse_non_negative_float(value, name):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a number."
        ) from exc

    if not isfinite(parsed) or parsed < 0:
        raise ValueError(
            f"{name} must be finite and non-negative."
        )

    return parsed


def _parse_retry_count(value, name):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be an integer."
        ) from exc

    if parsed < 0:
        raise ValueError(
            f"{name} must be non-negative."
        )

    return parsed


def _parse_historical_candle_count(value):
    parsed = _parse_optional_int(
        value,
        "HERMES_PAPER_HISTORICAL_CANDLES",
    )

    if parsed is None:
        return DEFAULT_HISTORICAL_CANDLES

    if parsed > MAX_HISTORICAL_CANDLES:
        raise ValueError(
            "HERMES_PAPER_HISTORICAL_CANDLES must be at most "
            f"{MAX_HISTORICAL_CANDLES}."
        )

    return parsed


def _load_fixture_provider(path, clock):
    with open(
        path,
        encoding="utf-8",
    ) as handle:
        fixtures = json.load(handle)

    return FixtureMarketDataProvider(
        fixtures,
        SnapshotBuilder(clock),
    )


def _market_trend_from_features(features: MarketFeatures):
    """
    Derive trend from deterministic technical evidence.

    EMA-12 versus EMA-26 is preferred when available. A final close
    comparison is used only as a deterministic fallback when the history
    is too short to calculate both EMAs.
    """

    if (
        features.ema_12 is not None
        and features.ema_26 is not None
    ):
        if features.ema_12 > features.ema_26:
            return "Bullish"

        if features.ema_12 < features.ema_26:
            return "Bearish"

        return "Sideways"

    if features.candle_count >= 2:
        return (
            "Bullish"
            if features.price > 0
            else "Sideways"
        )

    return "Sideways"


def _feature_snapshot(
    candles: tuple[PublicCandle, ...],
) -> MarketSnapshot:
    """
    Convert validated OHLCV history into the existing MarketSnapshot model.

    No synthetic sentiment or technical values are created. Any feature
    that cannot be calculated from the supplied history remains None.
    """

    if not candles:
        raise ValueError(
            "Cannot build a market snapshot from empty candle history."
        )

    features = build_market_features(candles)

    latest = candles[-1]

    previous_price = (
        candles[-2].close
        if len(candles) >= 2
        else None
    )

    volume_values = [
        float(candle.volume)
        for candle in candles
        if candle.volume is not None
    ]

    if not volume_values:
        volume_24h = 0.0
        average_volume = None
    else:
        # Four-hour candles: six bars represent approximately 24 hours.
        volume_24h = sum(
            volume_values[-6:]
        )

        average_volume = (
            sum(volume_values) / len(volume_values)
        )

    if features.realized_volatility is None:
        volatility = 0.0
    else:
        volatility = float(
            features.realized_volatility
        )

    market_trend = _market_trend_from_features(
        features
    )

    return MarketSnapshot(
        symbol=features.symbol,
        price=features.price,
        volume_24h=volume_24h,
        market_trend=market_trend,
        volatility=volatility,
        fear_greed_index=None,
        previous_price=previous_price,
        average_volume=average_volume,
        short_moving_average=features.sma_10,
        long_moving_average=features.sma_20,
        timeframe=features.timeframe,
        timestamp=latest.timestamp.astimezone(
            timezone.utc
        ),
    )


class PublicCandleMarketDataProvider:
    """
    Read-only historical public candle provider that exposes the
    MarketDataProvider snapshot interface used by PaperTradingSession.
    """

    def __init__(
        self,
        provider_group,
        builder,
        *,
        historical_candles=DEFAULT_HISTORICAL_CANDLES,
    ):
        self.provider_group = provider_group
        self.builder = builder
        self.historical_candles = historical_candles

        self.health = (
            provider_group.providers[0].health
            if provider_group.providers
            else ProviderHealth(
                False,
                "UNAVAILABLE",
                0,
                "No public providers configured.",
            )
        )

    def get_snapshot(
        self,
        symbol,
        timeframe="4H",
    ):
        candles = self.provider_group.get_candles(
            symbol,
            timeframe,
            limit=self.historical_candles,
        )

        if not candles:
            self.health = ProviderHealth(
                False,
                "UNAVAILABLE",
                1,
                "Public provider returned no historical candles.",
            )
            raise RuntimeError(
                "Public provider returned no historical candles."
            )

        snapshot = _feature_snapshot(
            tuple(candles)
        )

        selected_provider = candles[-1].provider

        for provider in self.provider_group.providers:
            if provider.name == selected_provider:
                self.health = provider.health
                break

        return snapshot


def _parse_public_adapters(value):
    names = tuple(
        item.strip().lower()
        for item in str(value).split(",")
        if item.strip()
    )

    if not names:
        raise ValueError(
            "HERMES_PAPER_PUBLIC_PROVIDERS must include at least one provider."
        )

    if len(set(names)) != len(names):
        raise ValueError(
            "HERMES_PAPER_PUBLIC_PROVIDERS must not contain duplicates."
        )

    unknown = tuple(
        name
        for name in names
        if name not in PUBLIC_ADAPTERS
    )

    if unknown:
        raise ValueError(
            "Unknown public provider(s): "
            + ", ".join(unknown)
            + "."
        )

    return names


def _print_batch(timestamp, results):
    statuses = ", ".join(
        f"{item.symbol}:{item.status}"
        for item in results
    )

    print(
        f"{timestamp.isoformat()} {statuses}",
        flush=True,
    )


def _load_public_provider(env, clock):
    names = _parse_public_adapters(
        env.get(
            "HERMES_PAPER_PUBLIC_PROVIDERS",
            "binanceus,coinbase,kraken",
        )
    )

    timeout = _parse_non_negative_float(
        env.get(
            "HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS",
            "5",
        ),
        "HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS",
    )

    retries = _parse_retry_count(
        env.get(
            "HERMES_PAPER_PUBLIC_RETRIES",
            "2",
        ),
        "HERMES_PAPER_PUBLIC_RETRIES",
    )

    historical_candles = _parse_historical_candle_count(
        env.get(
            "HERMES_PAPER_HISTORICAL_CANDLES",
            str(DEFAULT_HISTORICAL_CANDLES),
        )
    )

    if timeout <= 0:
        raise ValueError(
            "HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS must be positive."
        )

    adapters = tuple(
        PUBLIC_ADAPTERS[name](
            clock=clock,
            timeout=timeout,
            retries=retries,
        )
        for name in names
    )

    group = PublicProviderGroup(
        adapters
    )

    return (
        PublicCandleMarketDataProvider(
            group,
            SnapshotBuilder(clock),
            historical_candles=historical_candles,
        ),
        "public",
    )


def _load_market_provider(env, clock):
    fixture_path = env.get(
        "HERMES_PAPER_FIXTURES"
    )

    source = env.get(
        "HERMES_PAPER_DATA_SOURCE",
        "fixture" if fixture_path else "public",
    ).strip().lower()

    if source == "fixture":
        if not fixture_path:
            raise ValueError(
                "HERMES_PAPER_FIXTURES is required when "
                "HERMES_PAPER_DATA_SOURCE=fixture."
            )

        return (
            _load_fixture_provider(
                fixture_path,
                clock,
            ),
            "fixture",
        )

    if source == "public":
        if fixture_path:
            raise ValueError(
                "Set either HERMES_PAPER_DATA_SOURCE=fixture with "
                "fixtures or HERMES_PAPER_DATA_SOURCE=public without "
                "fixtures, not both."
            )

        return _load_public_provider(
            env,
            clock,
        )

    raise ValueError(
        "HERMES_PAPER_DATA_SOURCE must be fixture or public."
    )


def _load_operation_config(env):
    symbols = _parse_symbols(
        env.get(
            "HERMES_PAPER_SYMBOLS",
            ",".join(DEFAULT_SYMBOLS),
        )
    )

    timeframe = env.get(
        "HERMES_PAPER_TIMEFRAME",
        "4H",
    ).strip()

    interval_seconds = _parse_non_negative_float(
        env.get(
            "HERMES_PAPER_INTERVAL_SECONDS",
            "30",
        ),
        "HERMES_PAPER_INTERVAL_SECONDS",
    )

    max_failures = _parse_retry_count(
        env.get(
            "HERMES_PAPER_MAX_FAILURES",
            "3",
        ),
        "HERMES_PAPER_MAX_FAILURES",
    )

    recent_cycle_limit = _parse_retry_count(
        env.get(
            "HERMES_PAPER_RECENT_CYCLE_LIMIT",
            "100",
        ),
        "HERMES_PAPER_RECENT_CYCLE_LIMIT",
    )

    if not timeframe:
        raise ValueError(
            "HERMES_PAPER_TIMEFRAME must be non-empty."
        )

    if max_failures < 1:
        raise ValueError(
            "HERMES_PAPER_MAX_FAILURES must be positive."
        )

    if recent_cycle_limit < 1:
        raise ValueError(
            "HERMES_PAPER_RECENT_CYCLE_LIMIT must be positive."
        )

    return PaperOperationConfig(
        symbols=symbols,
        timeframe=timeframe,
        interval_seconds=interval_seconds,
        max_consecutive_failures=max_failures,
        recent_cycle_limit=recent_cycle_limit,
    )


def main(environ=None):
    env = os.environ if environ is None else environ

    settings = RuntimeSettings.from_env(
        env
    )

    journal = SQLiteAuditJournal(
        settings.database_path
    )

    journal.initialize()

    clock = lambda: datetime.now(timezone.utc)

    try:
        provider, source = _load_market_provider(
            env,
            clock,
        )

        config = _load_operation_config(
            env
        )

    except ValueError as exc:
        print(
            str(exc),
            flush=True,
        )
        return 2

    startup = StartupChecks(
        settings,
        journal,
        provider,
    ).run()

    if not startup.healthy:
        for check in startup.checks:
            print(
                f"{check.name}: "
                f"{check.healthy} "
                f"{check.detail}",
                flush=True,
            )

        return 1

    shutdown = GracefulShutdown()

    shutdown.install_signal_handlers()

    session = PaperTradingSession(
        provider,
        PaperPortfolio(
            clock=clock
        ),
        journal,
        clock,
    )

    operations = PaperOperationsService(
        session,
        journal,
        shutdown,
        clock=clock,
        on_batch=_print_batch,
    )

    print(
        "HERMES PAPER MODE SERVICE STARTED "
        f"data_source={source}",
        flush=True,
    )

    summary = operations.run(
        config,
        maximum_batches=_parse_optional_int(
            env.get(
                "HERMES_PAPER_MAX_BATCHES"
            ),
            "HERMES_PAPER_MAX_BATCHES",
        ),
    )

    print(
        "HERMES PAPER MODE SERVICE STOPPED "
        f"{summary.stopped_reason}",
        flush=True,
    )

    print(
        f"BATCHES {summary.batches_completed} "
        f"STATUSES {dict(summary.status_counts)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())