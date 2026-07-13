# Current Status

Development continues locally on `development/hermes-v2` after tagged Paper
Trading RC1. V2.1 governance is established; live trading remains prohibited.
The V2.2 command-center service provides immutable paper health, evidence, risk,
portfolio, performance, replay, and learning views without execution controls.
Public Binance.US, Coinbase, and Kraken observation adapters are optional,
unauthenticated, timeout-bounded, normalized, health-reported, and test-injected.
Liquidity, probability, and portfolio-context specialists now provide immutable,
explainable advisory assessments from validated supplied inputs.
Executive research briefings are available at daily, weekly, and monthly periods;
they are immutable, read-only, and never present paper results as live performance.
Research experiments require explicit scoped human approval before supplied paper
samples are evaluated, and their results cannot mutate production configuration.
Paper operations can recover the latest portfolio snapshot, run controlled foreground
batches, stop gracefully, and open a circuit after repeated complete batch failures.
Each persisted recommendation can now be translated into a human-readable explanation
of evidence, disagreement, exclusions, risk rationale, assumptions, and uncertainty.
A dedicated advisory regime engine now classifies bull, bear, sideways, accumulation,
distribution, breakout, breakdown, volatility, and transition conditions.
Validated 5m, 15m, 1h, 4h, and Daily specialist signals can now be composed into
short-, medium-, and long-term views with explicit alignment and conflict.

Hermes OS is at Paper Trading RC1 candidate status. It provides a synchronous,
paper-only multi-specialist decision, simulation, persistence, reporting,
learning-proposal, replay, health, backup, and container stack. Run
`python examples/workflows/morning_meeting.py` and test with
`python -m unittest discover -s tests -v`.

Paper eligibility is informational and cannot place a real order. Live trading,
exchange connections, API keys, and real execution are absent by design. Local
paper-order simulation and SQLite-backed portfolio restoration are implemented.

No authenticated exchange client, private API, funded-account connection,
withdrawal capability, or live order path exists. RC1 is long-only for simulated
positions because margin-safe short accounting is intentionally deferred.

Evidence is deterministic and explainable but uses initial static weights. Those
weights cannot be changed automatically and are not yet informed by scorecards.
