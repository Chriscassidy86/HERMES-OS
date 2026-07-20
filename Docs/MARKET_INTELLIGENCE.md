# Market Intelligence Framework

## Purpose

The Market Intelligence framework provides the foundation that Market
Intelligence agents inherit. It defines a standard advisory-only report
format, a base specialist interface, and the enums needed to classify market
regimes and agent operational status.

This framework is **advisory only**. It does not implement trading logic,
does not connect to exchanges, and does not produce buy/sell actions. Reports
produced by Market Intelligence specialists are evidence for human review.

## Architecture

### Module layout

```
models/market_intelligence.py              Domain models, enums, validation
agents/market_intelligence/__init__.py     Package init with specialist exports
agents/market_intelligence/base.py         Abstract base specialist interface
agents/market_intelligence/indicators.py  Deterministic indicator functions
agents/market_intelligence/trend_specialist.py       Trend Specialist
agents/market_intelligence/momentum_specialist.py    Momentum Specialist
agents/market_intelligence/volume_specialist.py      Volume Specialist
agents/market_intelligence/volatility_specialist.py  Volatility Specialist
tests/test_market_intelligence.py          Framework unit tests
tests/test_market_intelligence_specialists.py        Specialist unit tests
Docs/MARKET_INTELLIGENCE.md               This document
```

### Domain models

All models are **frozen dataclasses** (immutable) with validation in
`__post_init__`. They follow the same patterns as the existing consensus and
regime models:

- `MarketIntelligenceContext` — base context with `symbol`, `timeframe`, and
  UTC-aware `observed_at`. Future specialists may extend or compose this type.
- `MarketIntelligenceReport` — the standard report with `agent_name`, `symbol`,
  `timeframe`, `observed_at`, `confidence` (0.0–1.0), `evidence`,
  `conflicting_evidence`, `warnings`, `explanation`, and `advisory_only=True`.
  Includes a `create()` classmethod that rejects future timestamps and appends
  a stale-data warning when the observation exceeds the threshold. Provides
  `to_dict()`, `to_json()`, and `checksum()` for deterministic serialization.
- `Candle` — immutable OHLCV candle with UTC-aware `timestamp`, `open`,
  `high`, `low`, `close`, and `volume`. Validates that `low <= high`, that
  `open` and `close` are within `[low, high]`, that volume is non-negative,
  and that all numeric fields are finite.
- `TrendInputs`, `MomentumInputs`, `VolumeInputs`, `VolatilityInputs` —
  immutable specialist input dataclasses with `symbol`, `timeframe`,
  `observed_at`, and a tuple of validated `Candle` objects in ascending
  timestamp order.
- `SpecialistMetadata` — name, version, status, supported symbols/timeframes,
  and `advisory_only=True`.
- `HealthCheckResult` — agent name, status, healthy flag, explanation,
  checked-at timestamp, and `advisory_only=True`.

### Enums

#### `MarketRegime`

Scoped to the Market Intelligence framework. This is **distinct** from the
`MarketRegime` enum in `models/market_regime.py`, which serves the dedicated
regime classification engine with a different value set.

| Value | Description |
|---|---|
| `STRONG_BULL_TREND` | Strong upward directional pressure |
| `WEAK_BULL_TREND` | Mild upward directional pressure |
| `RANGE_BOUND` | Price confined to a range |
| `WEAK_BEAR_TREND` | Mild downward directional pressure |
| `STRONG_BEAR_TREND` | Strong downward directional pressure |
| `HIGH_VOLATILITY_TRANSITION` | Regime transition with elevated volatility |
| `INSUFFICIENT_DATA` | Not enough validated evidence to classify |

#### `AgentStatus`

| Value | Description |
|---|---|
| `ONLINE` | Specialist is online and ready |
| `OFFLINE` | Specialist is offline |
| `STARTING` | Specialist is starting up |
| `ERROR` | Specialist is in an error state |
| `DEGRADED` | Specialist is degraded but partially operational |

### Base specialist interface

`MarketIntelligenceSpecialist` (in `agents/market_intelligence/base.py`) is an
abstract base class that defines the contract for all intelligence agents:

| Member | Type | Description |
|---|---|---|
| `name` | property | Specialist name |
| `version` | property | Semantic version |
| `status` | property | Current `AgentStatus` |
| `supported_symbols` | property | Tuple of supported symbols |
| `supported_timeframes` | property | Tuple of supported timeframes |
| `analyze(context)` | abstract | Produce an advisory-only `MarketIntelligenceReport` |
| `health_check(now)` | method | Return a `HealthCheckResult` |
| `metadata()` | method | Return `SpecialistMetadata` |

The base class provides default implementations for `health_check` and
`metadata`. Subclasses must implement `analyze`.

### Serialization

All models support deterministic JSON serialization via `to_json()` and
`to_dict()`. `MarketIntelligenceReport` also provides a `checksum()` method
returning a SHA-256 hash of the deterministic JSON, suitable for tamper
detection and deduplication.

## Indicator functions

`agents/market_intelligence/indicators.py` contains pure, stateless,
deterministic indicator functions. No function performs I/O, networking, or
mutation. All functions return `None` when there is insufficient data.

| Function | Domain | Description |
|---|---|---|
| `sma(values, period)` | Trend | Simple moving average |
| `ema(values, period)` | Trend | Exponential moving average |
| `detect_swings(closes, lookback)` | Trend | Higher highs / lower lows detection |
| `rsi(closes, period)` | Momentum | Relative Strength Index (Wilder smoothing) |
| `macd(closes, fast, slow, signal)` | Momentum | MACD line, signal line, histogram |
| `stochastic(highs, lows, closes, k, d)` | Momentum | Stochastic %K and %D |
| `atr(highs, lows, closes, period)` | Volatility | Average True Range |
| `bollinger_bands(closes, period, std_dev)` | Volatility | Middle, upper, lower bands |
| `relative_volume(volumes, period)` | Volume | Current volume / average ratio |
| `volume_spikes(volumes, period, threshold)` | Volume | Count of abnormal volume bars |
| `obv(closes, volumes)` | Volume | Final On-Balance Volume value |
| `obv_series(closes, volumes)` | Volume | Full OBV series |

## Production specialists (Phase 2)

Four production Market Intelligence specialists are implemented. Each
inherits from `MarketIntelligenceSpecialist`, produces `MarketIntelligenceReport`
objects only, and remains advisory-only.

### Trend Specialist

**File:** `agents/market_intelligence/trend_specialist.py`

Evaluates only the trend domain:

- **EMA** — short EMA (12) vs. long EMA (26); bullish when short > long.
- **SMA** — short SMA (10) vs. long SMA (20); bullish when short > long.
- **Higher highs / lower lows** — swing structure detection over a 20-bar
  lookback.

Confidence is derived from the count of bullish vs. bearish signals, capped
at 0.85. Mixed signals cap confidence at 0.45.

### Momentum Specialist

**File:** `agents/market_intelligence/momentum_specialist.py`

Evaluates only the momentum domain:

- **RSI** — 14-period Wilder RSI; overbought >= 70 (bearish), oversold <= 30
  (bullish).
- **MACD** — 12/26/9; bullish when MACD line > signal line.
- **Stochastic** — 14/3; overbought >= 80 (bearish), oversold <= 20 (bullish);
  %K crossing %D adds directional evidence.

Confidence is derived from signal counts, capped at 0.80. Mixed signals cap
confidence at 0.45.

### Volume Specialist

**File:** `agents/market_intelligence/volume_specialist.py`

Evaluates only the volume domain:

- **Relative volume** — current volume / 20-bar average; high >= 1.5x, low <=
  0.5x.
- **Volume spikes** — count of bars exceeding 2x the preceding 20-bar
  average.
- **OBV** — On-Balance Volume trend; rising is bullish, falling is bearish.

Confidence is derived from signal counts, capped at 0.75. Mixed signals cap
confidence at 0.45.

### Volatility Specialist

**File:** `agents/market_intelligence/volatility_specialist.py`

Evaluates only the volatility domain:

- **ATR** — 14-period Average True Range as a fraction of price; high >= 3%,
  low <= 1%.
- **Bollinger Bands** — 20-period, 2 standard deviations; band width as a
  fraction of the middle band; high >= 10%, low <= 3%. Price position within
  bands is also reported.
- **Volatility regime** — classified as high, normal, or low based on ATR and
  Bollinger Band votes.

Confidence is 0.75 for high regime, 0.70 for low regime, 0.60 for normal
regime, and 0.20 when indeterminate.

## Safety boundaries

The Market Intelligence framework enforces the following safety boundaries:

- **Advisory only**: All reports, metadata, and health checks have
  `advisory_only=True` enforced in `__post_init__`. Setting it to `False`
  raises `ValueError`.
- **No exchange access**: No networking, no API clients, no credentials.
- **No API keys**: No secret-bearing configuration.
- **No portfolio mutation**: Reports are read-only evidence.
- **No Risk Manager mutation**: Reports cannot alter risk limits.
- **No order creation**: Reports contain no buy/sell directives.
- **Deterministic behavior**: Frozen dataclasses, UTC-aware timestamps,
  injected clocks, stable JSON serialization, and SHA-256 checksums.
- **Future timestamp rejection**: `MarketIntelligenceReport.create()` rejects
  observations dated after the injected `now` to prevent look-ahead bias.
- **Stale timestamp handling**: Observations older than the stale threshold
  (default 24 hours) are accepted but flagged with a warning.
- **Immutability**: All domain models are frozen dataclasses; mutation raises
  `FrozenInstanceError`.
- **Input validation**: `Candle` validates OHLCV consistency; specialist
  inputs validate non-empty candles and ascending timestamp order.
- **Insufficient data handling**: All indicator functions return `None` when
  data is insufficient; specialists append warnings and produce low-confidence
  reports.

## How to run

From `D:\Desktop\HERMES-OS` in PowerShell:

```powershell
# Run the framework tests
python -m unittest tests.test_market_intelligence -v

# Run the specialist tests
python -m unittest tests.test_market_intelligence_specialists -v
```

## Known limitations

- The `MarketRegime` enum here is separate from the regime engine's enum in
  `models/market_regime.py`. They serve different purposes and use different
  value sets.
- Stale data is flagged but not rejected; consumers must check warnings.
- No persistence layer is included; reports are in-memory only.
- Indicator functions use simple averaging for ATR (not Wilder smoothing for
  ATR; RSI does use Wilder smoothing).
- Specialists do not currently consume the `MarketIntelligenceContext` base
  type directly; they accept specialist-specific input dataclasses that carry
  validated candle tuples.
- No live-trading functionality exists or is planned for this framework.
