# HERMES-OS Architecture

Foundation II supplies configuration, logging, events, registry, scheduler, and
boot orchestration. Foundation III supplies frozen domain records, the
`BaseSpecialist` contract, Trend specialist, evidence aggregation,
recommendations, risk review, and briefing.

Foundation IV.1 adds `DecisionCycle` as the application boundary:

`MarketSnapshot -> Specialists -> DecisionPacket -> EvidenceSummary -> Recommendation -> RiskAssessment -> DecisionCycleResult`

It validates the snapshot and specialist responses, then returns an immutable
result containing every intermediate decision, cycle identity, final status,
rejection reasons, and paper eligibility. Exceptions, malformed outputs, empty
signals, invalid evidence, WAIT recommendations, and risk rejection fail closed.

The cycle has no exchange adapter, order model, execution service, live-data
connection, or persistent portfolio.

Foundation IV.2 makes the intelligence layer multi-specialist. Trend, Market
Regime, Momentum, Volume, and Volatility produce timestamped evidence using the
same immutable snapshot. `EvidenceAnalyzer` applies explicit specialist weight,
source reliability, confidence, strength, freshness, and timeframe compatibility.
Neutral evidence is recorded but excluded from directional confidence. The
summary exposes contributions, conflicts, exclusions, directional score, and
final confidence so every recommendation remains explainable.

Foundation IV.3 adds an in-memory `PaperPortfolio` aggregate and immutable
account, position, order, fill, trade, and transition records. A proposal must
carry directional cycle eligibility and Risk Manager approval. Deterministic
market fills apply configured fees and slippage, update cash and exposure, and
record every state transition. Short selling is rejected until its accounting
and margin model can be proven safe. No exchange interface exists.

Foundation IV.4 adds a persistence abstraction boundary through
`SQLiteAuditJournal`. Schema-versioned, transaction-safe SQLite records capture
cycles and every decision artifact plus portfolio state and rejection history.
Serialization is deterministic JSON with UTC timestamps. Initialization is
explicit and duplicate cycle identifiers fail closed.

Foundation V.1 introduces the `MarketDataProvider` boundary, snapshot builder,
fixture and replay providers, and a credential-free read-only public wrapper.
Deterministic fixtures remain the default. Required fields, normalization,
freshness, retries, timeout, and provider health all fail closed.

Foundation V.2 composes provider, decision cycle, Risk Manager, paper portfolio,
SQLite journal, and health reporting in `PaperTradingSession`. Duplicate cycles
are persisted before execution and suppressed. `ScheduledPaperSession.run_once`
is synchronous, injected-clock, and failure-isolated with no background threads.

Foundation VI evaluates closed paper outcomes with deterministic strategy and
specialist scorecards, drawdown, expectancy, profit factor, calibration, and
daily/weekly reports. `LearningEngine` only emits immutable proposed
configuration patches with evidence, sample size, estimates, confidence, risks,
and mandatory human approval. It has no configuration write path.

Foundation VII adds read-only `OperatorReports` and a JSON CLI for system state,
latest decisions/evidence, paper portfolio, positions, trades, P&L, scorecards,
rejections, risk, and provider health. Reports reuse journal and performance
services; no business logic or trading controls exist in the interface.

Foundation VIII adds deterministic historical candle loading, replay clock,
session, paper fee/slippage model, equity history, benchmark comparison, metrics,
and trade/decision exports. A decision receives only the current candle-derived
snapshot; the next candle is read only after the decision to evaluate outcome,
preventing look-ahead access.

Foundation IX hardens paper operation with validated environment settings,
non-overridable paper mode, rotating JSON logs, startup/database/provider checks,
graceful shutdown state, validated SQLite backup/restore, non-root container
files, healthcheck, and non-deploying CI tests and secret scanning.
