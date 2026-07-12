# Changelog

## Foundation IX - Paper Production Hardening

- Added typed paper-only environment settings and rotating structured logs.
- Added startup/health/shutdown and validated SQLite backup/restore.
- Added non-root Docker/Compose healthchecks and non-deploying CI safety checks.

## Foundation VIII - Deterministic Backtest and Replay Framework

- Added historical fixture loading, replay clock/session, metrics, benchmark, and exports.
- Enforced decision-time versus future-outcome separation and deterministic costs.

## Foundation VII - Operator Reports and Paper Dashboard Foundation

- Added read-only JSON reports for decisions, evidence, portfolio, trades, P&L,
  scorecards, rejections, risk, provider health, and system status.
- Added a local CLI without exchange controls or web assets.

## Foundation VI - Performance and Learning Engine

- Added paper outcome, strategy, specialist, drawdown, and period reports.
- Added deterministic P&L, expectancy, profit factor, drawdown, and calibration.
- Added human-review configuration proposals that cannot mutate production rules.

## Foundation V.2 - Orchestrated Paper Trading Sessions

- Composed validated data, specialists, risk, paper execution, persistence, and health.
- Added duplicate suppression, restart state reload, and synchronous scheduling.

## Foundation V.1 - Validated Market Data Providers

- Added deterministic fixture and replay providers.
- Added normalization, snapshot validation, freshness, retries, and health state.
- Added a credential-free read-only public-data boundary; tests remain offline.

## Foundation IV.4 - SQLite Audit Journal and Persistence

- Added explicit schema versioning and initialization.
- Added transactional cycle and paper-portfolio persistence.
- Added deterministic serialization, duplicate protection, and query commands.

## Foundation IV.3 - Persistent Paper Portfolio Lifecycle

- Added paper accounts, positions, orders, fills, trades, and transition records.
- Added deterministic market-fill fees and slippage.
- Added cash, equity, exposure, and P&L accounting.
- Enforced cycle eligibility, Risk Manager veto, and safe long-only behavior.

## Foundation IV.2 - Weighted Multi-Specialist Intelligence

- Added Market Regime, Momentum, Volume, and Volatility specialists.
- Extended snapshots and signals with timeframe, timestamp, and evidence inputs.
- Added explicit weight, reliability, freshness, strength, and timeframe handling.
- Added contribution, conflict, exclusion, directional-score, and confidence explanations.

## Foundation IV.1 - Paper-Only Operational Decision Cycle

- Added validated `DecisionCycle` and immutable `DecisionCycleResult`.
- Made decision-packet signals immutable.
- Added minimal bearish handling to the Trend specialist.
- Replaced the hardcoded morning meeting with a real pipeline example.
- Added decision-cycle tests and operational/safety documentation.
