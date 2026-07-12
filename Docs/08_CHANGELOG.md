# Changelog

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
