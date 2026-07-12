# HERMES-OS

HERMES-OS is an experimental Python multi-agent crypto decision system. The
current release implements Foundation IV.2: deterministic weighted
multi-specialist intelligence in a synchronous, paper-only decision cycle.

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
