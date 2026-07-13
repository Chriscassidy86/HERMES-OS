# HERMES-OS Architecture

## Governance layer

Company, engineering, AI, and risk governance constrain every application layer.
Human approval controls releases and configuration adoption; deterministic Risk
Manager veto controls paper eligibility. Presentation and provider code cannot
bypass domain services.

## Command center service

`CommandCenterService` creates an immutable, read-only operator/CEO view from the
audit journal, provider health, replay state, and learning proposals. It exposes
no action callbacks and keeps presentation concerns outside domain logic.

V2.3 adds injected, unauthenticated Binance.US, Coinbase, and Kraken public candle
adapters plus normalized comparison and deterministic failover. No adapter exposes
credentials or an order method; offline fixtures remain the test default.

V2.4 adds immutable validated inputs and advisory assessments for quoted liquidity,
bounded evidence probability, and paper-portfolio concentration. These specialists
are deliberately outside the authoritative decision and Risk Manager path; human
review is required before research observations influence configuration.

V2.5 builds immutable daily, weekly, and monthly executive research briefings
from supplied validated facts and advisory assessments. Briefing generation is
read-only presentation logic and always preserves paper-result limitations.

V2.6 provides immutable paper research definitions, scoped human approvals,
unique observations, and deterministic baseline/candidate results. Experiment
completion cannot apply configuration; adoption remains a separate human decision.

V2.7 adds a foreground, recovery-aware paper operations service with graceful
shutdown, bounded summaries, and a consecutive-failure circuit breaker. SQLite
integrity and backups are verified, and the operator CLI exposes read-only integrity.

V3.1 adds a deterministic explanation service over immutable decision artifacts.
Command-center and briefing presentation reuse that service; they do not reimplement
decision, evidence, or risk logic.

V3.2 adds a dedicated regime research boundary with immutable validated inputs and
classification results. Explicit ordered rules classify trend, range, flow,
break, volatility, and transition regimes without altering trading eligibility.

V3.3 adds a multi-timeframe aggregation boundary over supplied specialist signals.
It explains short-, medium-, and long-term views per specialist; the recommendation
engine requires complete alignment and still sends any direction to Risk Manager.

V3.4 composes the command-center, explanation, regime, multi-timeframe, learning,
and experiment artifacts into an immutable CEO dashboard view. The renderer only
serializes that view and contains no health, recommendation, risk, or portfolio logic.

V3.5 adds a post-trade learning explanation engine over validated closed paper
outcomes. It emits immutable causal observations, specialist correctness,
calibration, and repeated-pattern reports with no configuration write boundary.

V3.6 adds a dedicated research-provenance boundary alongside the operational audit
journal. `ResearchRepository` owns explicitly versioned SQLite metadata plus dataset,
run, and typed artifact tables. Initialization and migration are explicit; imports
never write. Canonical UTC JSON and SHA-256 checksums make datasets, manifests, and
exports stable and tamper-evident. Writes are transactional and exact retries are
idempotent, while conflicting identifiers fail closed.

`ResearchRunOrchestrator` accepts only cataloged and checksum-verified fixture,
replay, public-observation, or paper datasets. It evaluates multiple symbols,
timeframes, and immutable baseline/candidate configurations without network access.
Walk-forward splitting enforces ordered, non-overlapping training, validation, and
test windows. Comparison and calibration services remain advisory and cannot mutate
configuration. The localhost dashboard adapter accepts GET only and delegates all
business composition to the CEO dashboard service.
V4.1 adds an immutable web projection service and presentation-only HTML/JSON renderer over the localhost GET-only server.
V4.2 adds a visualization projection service; frontend endpoints only serialize validated UTC chart series and never fetch market data.
V4.3 adds an immutable bounded research-job state machine over the V3.6 repository and orchestrator.
V4.4 adds immutable performance observations and a deterministic analytics service outside the UI.
V4.5 adds local alert detection and an immutable PAPER operator checklist; external delivery is disabled.
V4.6 hardens loopback delivery, bounded research identity, UTC analytics, and release operations.
V5.1 designates `PaperOperationsService` as the continuous market engine, preserving the existing session, decision, risk, portfolio, and journal pipeline.
V5 connects that engine to explainable paper execution, the GET-only live dashboard, recommendation-only learning, and an accelerated reliability harness. Risk Manager remains the sole execution gate.
V6.1 adds a fair scheduler above the existing session, with isolated per-symbol runtime state and one recovered shared PAPER portfolio.
V6.2 composes existing unauthenticated candle adapters behind per-symbol health, cooldown, conflict validation, and deterministic priority.
V6 completes one shared-portfolio PAPER pipeline: fair multi-symbol scheduling, attributed public redundancy, Risk-gated realistic simulation, portfolio projections, and reproducible soak artifacts.

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
