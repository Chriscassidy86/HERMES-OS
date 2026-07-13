# HERMES-OS

Hermes OS is built by **Hermes Quant Labs** under the policies in
`Docs/HERMES_COMPANY_MANUAL.md`. Release identity is recorded in `VERSION.md` and
planned V2 milestones are in `Docs/V2_ROADMAP.md`.
Operators can compose a read-only system view with
`services.command_center.CommandCenterService`; it contains no trading controls.
Optional public candle observation adapters support Binance.US, Coinbase, and
Kraken without authentication; tests use injected fixtures and never need internet.
V2.4 adds validated advisory liquidity, probability, and portfolio-context
assessments. They cannot change evidence weights, risk limits, or execution state.
Daily, weekly, and monthly executive research briefs can be rendered with
`python examples/research_briefings_demo.py` from explicitly supplied paper facts.
Governed paper experiments require a scoped human approval record before evaluation;
run `python examples/research_experiment_demo.py` for a deterministic example.
Recovery-aware paper operations with failure circuit breaking are demonstrated by
`python examples/paper_operations_demo.py`; database integrity is operator-readable.
V3.1 adds immutable human-readable decision explanations covering evidence,
agreement, disagreement, exclusions, Risk Manager rationale, assumptions, and uncertainty.
V3.2 adds an explainable deterministic market-regime research engine covering ten
regimes and failing closed when supplied evidence is insufficient or contradictory.
V3.3 aggregates validated specialist evidence across 5m, 15m, 1h, 4h, and Daily
horizons and returns `WAIT` whenever timeframe or specialist alignment conflicts.
V3.4 adds an immutable, read-only CEO dashboard projection and JSON renderer with
PAPER banner, portfolio, specialists, regime, recommendation, risk, health, learning,
and experiment status; it exposes no actions.
V3.5 adds immutable post-trade explanations for successful and losing paper trades,
specialist correctness, confidence calibration, and recurring mistakes without
automatically changing strategies, weights, risk limits, or configuration.
V3.6 adds a versioned research repository, immutable dataset catalog, deterministic
run manifests, walk-forward splits, run/dataset/configuration comparisons, stable
reproducibility exports, calibration monitoring, and localhost-only GET dashboard delivery.

Run the V3.6 examples with:

```powershell
python examples/catalog_dataset_demo.py
python examples/research_job_demo.py
python examples/walk_forward_demo.py
python examples/research_comparison_demo.py
python examples/reproducibility_export_demo.py
python examples/local_dashboard_demo.py
```

To serve an existing journal locally, run
`python scripts/read_only_dashboard.py data/hermes.sqlite3`. Only `GET /dashboard`
and `GET /health` are supported; the listener binds to `127.0.0.1`.
V4.1 adds stable HTML and JSON CEO dashboard views with all composition performed by `WebDashboardService`.
V4.2 adds validated, labeled, paginated and downsampled chart projections for market, specialist, risk, portfolio, P&L, trade, and calibration histories.
V4.3 adds a bounded local replay/research workspace with deterministic jobs, cancellation, persisted manifests, comparisons, and exports.
V4.4 adds deterministic advanced performance analytics with explicit sample gates and source separation.
V4.5 adds local structured alerts and the 12-step PAPER daily operator workflow.
V4.6 restricts dashboard binding at the API boundary, strengthens research input identity/bounds, enforces UTC analytics, and completes operator documentation.
V5.1 extends the recovered paper operations loop with bounded cycle metrics, stale-data rejection, and read-only batch updates.
V5.2 adds an explainable Risk-gated facade over the existing deterministic paper portfolio.

HERMES-OS is an experimental Python multi-agent crypto decision system. The
current release is the Paper Trading RC1 candidate, incorporating Foundations
IV.1 through X in a synchronous, paper-only platform.

## Implemented architecture

`MarketSnapshot -> Specialists -> DecisionPacket -> EvidenceSummary -> Recommendation -> RiskAssessment -> DecisionCycleResult`

Foundation II provides configuration, logging, events, a registry, a scheduler,
and boot orchestration. Foundation III provides domain models, the Trend
specialist, evidence aggregation, recommendation logic, risk review, and an
executive brief. Foundation IV.1 connects those pieces through `DecisionCycle`.
Foundation IV.2 runs Trend, Market Regime, Momentum, Volume, and Volatility
specialists and records every weighted contribution and exclusion.

## Run the decision cycle

```powershell
python examples/workflows/morning_meeting.py
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

Run the isolated simulated portfolio example with
`python examples/paper_portfolio_demo.py`.

Run `python examples/audit_journal_demo.py` to initialize a local SQLite audit
journal and save one supplied-data cycle. No network or exchange is contacted.

The project currently uses only the Python standard library.

## Safety boundary

- Paper execution eligibility is a decision flag only; it does not place orders.
- No broker, exchange, API-key, or Binance.US integration exists.
- `LIVE_TRADING` remains `False`.
- Invalid or empty evidence and risk rejection always prevent eligibility.
- Paper orders are local deterministic simulations only; no exchange is contacted.

Run `python examples/market_data_demo.py` for the deterministic fixture provider.

Run `python examples/paper_session_demo.py` for one complete persisted paper-only session.

Run `python examples/performance_learning_demo.py` to calculate paper performance
and emit a human-review-only learning proposal.

Use `python -m reports.operator_cli <database> <report>` for read-only local JSON reports.

Run `python examples/replay_demo.py` for an artificial deterministic fixture.
Fixture results are never presented as evidence of real profitability.

See `Docs/DEPLOYMENT.md` for paper-only Docker and VPS guidance. Live mode is
rejected by configuration validation and no exchange credentials are supported.

RC1 operations, safety, incident response, and release limitations are documented
under `Docs/`. `FOUNDATIONS.md` records milestone acceptance and local commits.

## Current limitations

- Specialist rules are intentionally simple deterministic heuristics.
- Evidence weights and source reliability are explicit static configuration.
- Risk rules use fixed demonstration limits rather than portfolio state.
- Fixture and replay market data are supported; no default internet provider is configured.
- SQLite persistence is local and synchronous.
