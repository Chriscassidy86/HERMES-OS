"""Governed adapters that create advisory observations without trading access."""

from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite

from data_providers.public_adapters import RateLimitError
from models.consensus_registry import ConsensusSourceRecord
from models.market_consensus import ConsensusDirection, ConsensusObservation, ConsensusSignal, ConsensusSource, SourceCategory, SourceHealth, stable_json, utc


class ConsensusAdapterError(ValueError):
    pass


def _direction(score: float) -> ConsensusDirection:
    if score <= -0.75:
        return ConsensusDirection.STRONG_BEARISH
    if score <= -0.4:
        return ConsensusDirection.BEARISH
    if score < -0.1:
        return ConsensusDirection.LEAN_BEARISH
    if score < 0.1:
        return ConsensusDirection.NEUTRAL
    if score < 0.4:
        return ConsensusDirection.LEAN_BULLISH
    if score < 0.75:
        return ConsensusDirection.BULLISH
    return ConsensusDirection.STRONG_BULLISH


def _source(record: ConsensusSourceRecord, *, enabled: bool, data_label: str | None = None) -> ConsensusSource:
    return ConsensusSource(record.source_id, record.display_name, record.category, record.default_reliability, "GOVERNED", data_label or record.source_status, record.terms_note, enabled, record.known_limitations)


class ExistingMarketEvidenceAdapter:
    """Derive evidence only from snapshots already validated by Hermes providers."""

    def __init__(self, record: ConsensusSourceRecord, *, clock):
        if record.approved_access_method != "EXISTING_VALIDATED_SNAPSHOT":
            raise ConsensusAdapterError("Existing-market adapter requires governed snapshot access.")
        self.record = record
        self.source = _source(record, enabled=True)
        self.clock = clock

    def observations(self, snapshots, *, timeframe: str) -> tuple[ConsensusObservation, ...]:
        now = utc(self.clock(), "clock")
        rows = tuple(snapshots)
        if not rows:
            raise ConsensusAdapterError("Validated public snapshots are required.")
        result = []
        directions = []
        for snapshot in sorted(rows, key=lambda item: item.symbol):
            if snapshot.timeframe != timeframe:
                raise ConsensusAdapterError("Snapshot timeframe mismatch.")
            observed = utc(snapshot.source_timestamp or snapshot.timestamp, "snapshot source timestamp")
            price_change = (snapshot.price - snapshot.previous_price) / snapshot.previous_price if snapshot.previous_price and snapshot.previous_price > 0 else 0
            metrics = (
                ("price-trend", max(-1.0, min(1.0, price_change * 20)), price_change, "Price change versus the prior validated close."),
                ("relative-volume", max(-1.0, min(1.0, snapshot.volume_24h / snapshot.average_volume - 1)) if snapshot.average_volume and snapshot.average_volume > 0 else 0, snapshot.volume_24h, "Volume relative to the supplied validated baseline."),
                ("volatility", 0.0, snapshot.volatility, "Volatility is recorded as uncertainty and not directional evidence."),
                ("momentum", 0.35 if snapshot.market_trend.lower().startswith("bull") else (-0.35 if snapshot.market_trend.lower().startswith("bear") else 0), snapshot.market_trend, "Momentum mapped from the existing validated market trend."),
            )
            for metric, score, raw, explanation in metrics:
                signal = ConsensusSignal(_direction(score), round(score, 6), 0.7 if metric != "volatility" else 0.4, min(1.0, abs(score)), (explanation, "Exchange-derived observations may share an underlying dataset."))
                result.append(ConsensusObservation.create(observation_id=self._id(snapshot.symbol, timeframe, observed, metric), source=self.source, symbol=snapshot.symbol, timeframe=timeframe, observed_at=observed, ingested_at=now, raw_value=str(raw), signal=signal, reference=snapshot.source, underlying_dataset=f"validated-market:{snapshot.symbol}:{observed.isoformat()}"))
            directions.append(price_change)
        breadth = sum(1 if value > 0 else (-1 if value < 0 else 0) for value in directions) / len(directions)
        breadth_source = ConsensusSource(self.source.source_id + "-breadth", self.source.display_name + " Breadth", SourceCategory.MARKET_BREADTH, self.source.default_reliability, self.source.trust_level, self.source.data_label, self.source.provenance, True, ("Breadth uses the same underlying validated market snapshots.",))
        signal = ConsensusSignal(_direction(breadth), round(breadth, 6), min(0.75, 0.4 + len(rows) * 0.08), abs(breadth), ("Breadth covers only enabled Hermes symbols.",))
        result.append(ConsensusObservation.create(observation_id=self._id("MARKET-WIDE", timeframe, now, "breadth"), source=breadth_source, symbol="MARKET-WIDE", timeframe=timeframe, observed_at=now, ingested_at=now, raw_value=breadth, signal=signal, underlying_dataset="validated-market-enabled-symbols"))
        return tuple(sorted(result, key=lambda item: (item.source_id, item.symbol, item.observation_id)))

    def provider_comparison(self, comparison, *, symbol: str, timeframe: str) -> ConsensusObservation:
        now = utc(self.clock(), "clock")
        if not comparison.candles:
            raise ConsensusAdapterError("Provider comparison has no validated candles.")
        observed = max(utc(item.timestamp, "provider timestamp") for item in comparison.candles)
        spread = float(comparison.price_spread_percent)
        score = max(-1.0, 1.0 - spread / 2.0)
        warning = () if spread <= 1 else ("Cross-provider price disagreement is elevated.",)
        signal = ConsensusSignal(_direction(score), score, min(1.0, len(comparison.candles) / 3), abs(score), ("Agreement is a data-quality observation, not price direction.",))
        return ConsensusObservation.create(observation_id=self._id(symbol, timeframe, observed, "provider-agreement"), source=self.source, symbol=symbol, timeframe=timeframe, observed_at=observed, ingested_at=now, raw_value=spread, signal=signal, reference=",".join(sorted(item.provider for item in comparison.candles)), warnings=warning, underlying_dataset=f"provider-comparison:{symbol}:{observed.isoformat()}")

    @staticmethod
    def _id(symbol, timeframe, observed, metric):
        value = stable_json((symbol, timeframe, observed.isoformat(), metric))
        return "MARKET-" + sha256(value.encode("utf-8")).hexdigest()[:20]


class InjectedPublicConsensusAdapter:
    """Parse an official public JSON payload through an injected transport only."""

    def __init__(self, record: ConsensusSourceRecord, transport, *, clock, timeout: float = 5.0, retries: int = 1):
        if record.approved_access_method != "OFFICIAL_PUBLIC_ENDPOINT" or transport is None:
            raise ConsensusAdapterError("A governed official endpoint and injected transport are required.")
        if timeout <= 0 or retries < 0 or retries > 3:
            raise ConsensusAdapterError("Public adapter retry controls are invalid.")
        self.record = record
        self.transport = transport
        self.clock = clock
        self.timeout = timeout
        self.retries = retries
        self.health = SourceHealth(record.source_id, utc(clock(), "clock"), "READY", None, 0, False, "No request attempted.")

    def fetch(self, symbol: str, timeframe: str) -> ConsensusObservation:
        if symbol not in self.record.supported_symbols or timeframe not in self.record.supported_timeframes:
            raise ConsensusAdapterError("Consensus source does not support the requested symbol or timeframe.")
        error = None
        for attempt in range(self.retries + 1):
            try:
                payload = self.transport.get(self.record.official_homepage, self.timeout)
                result = self._parse(payload, symbol, timeframe)
                self.health = SourceHealth(self.record.source_id, utc(self.clock(), "clock"), "HEALTHY", None, 0, False, f"Public payload accepted on attempt {attempt + 1}.")
                return result
            except RateLimitError as exc:
                self.health = SourceHealth(self.record.source_id, utc(self.clock(), "clock"), "RATE_LIMITED", None, attempt + 1, True, str(exc))
                raise ConsensusAdapterError("Consensus source rate limited the request.") from exc
            except (ConsensusAdapterError, TimeoutError, OSError, TypeError, ValueError, KeyError, IndexError) as exc:
                error = exc
        self.health = SourceHealth(self.record.source_id, utc(self.clock(), "clock"), "UNAVAILABLE", None, self.retries + 1, False, str(error))
        raise ConsensusAdapterError(f"Consensus source unavailable: {error}") from error

    def _parse(self, payload, symbol, timeframe):
        raise NotImplementedError


class FearGreedFixtureAdapter(InjectedPublicConsensusAdapter):
    def _parse(self, payload, symbol, timeframe):
        row = payload["data"][0]
        value = float(row["value"])
        if not isfinite(value) or not 0 <= value <= 100:
            raise ConsensusAdapterError("Fear and Greed value is malformed.")
        observed = datetime.fromtimestamp(int(row["timestamp"]), timezone.utc)
        score = (value - 50) / 50
        source = _source(self.record, enabled=True, data_label="FIXTURE")
        signal = ConsensusSignal(_direction(score), score, 0.45, abs(score), ("Broad-market sentiment has deliberately limited confidence.", "Classification is supplied by the source."))
        return ConsensusObservation.create(observation_id=f"FNG-{int(observed.timestamp())}", source=source, symbol=symbol, timeframe=timeframe, observed_at=observed, ingested_at=utc(self.clock(), "clock"), raw_value=f"{value}:{row.get('value_classification', 'UNKNOWN')}", signal=signal, reference=self.record.official_homepage, warnings=("Fixture parser only; production source remains disabled pending access review.",), underlying_dataset="fear-greed-broad-market")


class CoinGeckoFixtureAdapter(InjectedPublicConsensusAdapter):
    def _parse(self, payload, symbol, timeframe):
        change = float(payload["price_change_percentage_24h"])
        rank = int(payload["market_cap_rank"])
        volume = float(payload["total_volume"])
        observed = utc(datetime.fromisoformat(payload["last_updated"]), "last_updated")
        if not isfinite(change) or not isfinite(volume) or rank <= 0 or volume < 0:
            raise ConsensusAdapterError("Public metadata payload is malformed.")
        score = max(-1.0, min(1.0, change / 10))
        source = _source(self.record, enabled=True, data_label="FIXTURE")
        signal = ConsensusSignal(_direction(score), score, 0.5, abs(score), ("Market metadata is contextual and not executable evidence.",))
        return ConsensusObservation.create(observation_id=f"CG-{symbol.replace('/', '-')}-{int(observed.timestamp())}", source=source, symbol=symbol, timeframe=timeframe, observed_at=observed, ingested_at=utc(self.clock(), "clock"), raw_value=f"change={change};rank={rank};volume={volume}", signal=signal, reference=self.record.official_homepage, warnings=("Fixture parser only; production source remains disabled pending access review.",), underlying_dataset="coingecko-market-metadata")


class FixtureConsensusAdapter:
    def __init__(self, record: ConsensusSourceRecord, *, clock):
        if record.implementation_status != "FIXTURE_ONLY":
            raise ConsensusAdapterError("Fixture adapter requires fixture-only governance.")
        self.record = record
        self.clock = clock

    def observation(self, record: dict) -> ConsensusObservation:
        now = utc(self.clock(), "clock")
        symbol = record.get("symbol")
        timeframe = record.get("timeframe")
        if symbol not in self.record.supported_symbols or timeframe not in self.record.supported_timeframes:
            raise ConsensusAdapterError("Fixture symbol or timeframe is unsupported.")
        score = float(record["score"])
        source = _source(self.record, enabled=True, data_label="FIXTURE")
        signal = ConsensusSignal(_direction(score), score, float(record.get("confidence", 0.5)), min(1.0, abs(score)), ("Deterministic fixture; not a live market observation.",))
        return ConsensusObservation.create(observation_id=record["observation_id"], source=source, symbol=symbol, timeframe=timeframe, observed_at=utc(record["observed_at"], "observed_at"), ingested_at=now, raw_value=record.get("raw_value"), signal=signal, reference="FIXTURE", warnings=("FIXTURE ONLY",), underlying_dataset=record.get("underlying_dataset", self.record.source_id))


class ManualImportConsensusAdapter:
    def __init__(self, record: ConsensusSourceRecord, *, clock):
        if record.implementation_status != "IMPORT_ONLY":
            raise ConsensusAdapterError("Manual import adapter requires import-only governance.")
        self.record = record
        self.clock = clock

    def observation(self, record: dict) -> ConsensusObservation:
        required = ("observation_id", "symbol", "timeframe", "observed_at", "direction", "score", "confidence", "author", "reference", "summary")
        if any(not record.get(key) and record.get(key) != 0 for key in required):
            raise ConsensusAdapterError("Manual import is missing required attribution or evidence.")
        if len(record["summary"]) > 280:
            raise ConsensusAdapterError("Manual import summary exceeds the compliant bound.")
        if record["symbol"] not in self.record.supported_symbols or record["timeframe"] not in self.record.supported_timeframes:
            raise ConsensusAdapterError("Manual import symbol or timeframe is unsupported.")
        observed = utc(record["observed_at"], "observed_at")
        now = utc(self.clock(), "clock")
        stale = (now - observed).total_seconds() > self.record.freshness_threshold_seconds
        direction = ConsensusDirection(record["direction"])
        signal = ConsensusSignal(direction, float(record["score"]), float(record["confidence"]), min(1.0, abs(float(record["score"]))), ("Imported methodology and expertise are not independently verified.",))
        source = _source(self.record, enabled=True, data_label="EXPORT")
        return ConsensusObservation.create(observation_id=record["observation_id"], source=source, symbol=record["symbol"], timeframe=record["timeframe"], observed_at=observed, ingested_at=now, raw_value=record["summary"], signal=signal, reference=f"{record['author']}|{record['reference']}", eligible_for_consensus=not stale, exclusion_reason="STALE_IMPORT" if stale else None, warnings=("Popularity does not establish expertise.",) if self.record.category is SourceCategory.ANALYST_COMMUNITY else (), underlying_dataset=record.get("underlying_dataset", self.record.source_id))
