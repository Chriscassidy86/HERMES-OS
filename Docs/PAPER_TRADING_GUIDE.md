# Paper Trading Guide

Use deterministic fixture or replay data for tests, and unauthenticated public
read-only candles for operator PAPER observation runs. A session validates market
data, runs five specialists, weights evidence, obtains a recommendation, applies
the Risk Manager veto, proposes a local order, simulates fees/slippage, persists
the audit trail, and returns health state.

`paper_execution_eligible` is necessary but never sufficient without current
Risk Manager approval. Simulated cash, size, and price checks can still reject a
proposal. Short simulation is rejected. Public exchange endpoints may be used
only for unauthenticated read-only candles; no authenticated account or order
endpoint is used. Entry, mark, and close prices must be finite and positive; invalid marks are
rejected without mutating the simulated position or account.

Artificial replay profit is test output, not a profitability claim. Learning
output is a proposal requiring human approval and never changes production rules.

## Foreground service handoff

`scripts/paper_service.py` is the final operator handoff entrypoint for PAPER
mode. It initializes and validates the SQLite journal, restores the paper portfolio
through `PaperOperationsService`, and then runs bounded or continuous batches
until shutdown, batch limit, or the failure circuit stops it. By default it uses
unauthenticated, read-only public candle adapters for paper observation. Set
`HERMES_PAPER_DATA_SOURCE=fixture` with `HERMES_PAPER_FIXTURES` for deterministic
operator trials. It never accepts exchange credentials and cannot submit orders
to any exchange.

Useful environment variables:

- `HERMES_DATABASE`: SQLite paper journal path.
- `HERMES_PAPER_DATA_SOURCE`: `public` or `fixture`; defaults to `fixture` when
  `HERMES_PAPER_FIXTURES` is set, otherwise `public`.
- `HERMES_PAPER_FIXTURES`: JSON mapping of symbols to market snapshots; required
  only when `HERMES_PAPER_DATA_SOURCE=fixture`.
- `HERMES_PAPER_SYMBOLS`: comma-separated symbols; defaults to BTC, ETH, SOL,
  and XRP USD markets.
- `HERMES_PAPER_TIMEFRAME`: default `4H`.
- `HERMES_PAPER_INTERVAL_SECONDS`: delay between batches; default `30`.
- `HERMES_PAPER_MAX_BATCHES`: optional positive integer for a bounded trial run.
- `HERMES_PAPER_MAX_FAILURES`: consecutive complete batch failures before the
  local circuit opens; default `3`.
- `HERMES_PAPER_PUBLIC_PROVIDERS`: comma-separated public providers for public
  observation mode; supported values are `binanceus`, `coinbase`, and `kraken`.
- `HERMES_PAPER_PUBLIC_TIMEOUT_SECONDS`: public request timeout; default `5`.
- `HERMES_PAPER_PUBLIC_RETRIES`: public provider retries; default `2`.

Example bounded public handoff run:

```bash
HERMES_DATABASE=data/hermes.sqlite3 \
HERMES_PAPER_DATA_SOURCE=public \
HERMES_PAPER_SYMBOLS=BTC/USD,ETH/USD,SOL/USD,XRP/USD \
HERMES_PAPER_MAX_BATCHES=1 \
python scripts/paper_service.py
```

Example bounded fixture handoff run:

```bash
HERMES_DATABASE=data/hermes.sqlite3 \
HERMES_PAPER_DATA_SOURCE=fixture \
HERMES_PAPER_FIXTURES=data/paper_fixtures.json \
HERMES_PAPER_SYMBOLS=BTC/USD,ETH/USD,SOL/USD,XRP/USD \
HERMES_PAPER_MAX_BATCHES=1 \
python scripts/paper_service.py
```
