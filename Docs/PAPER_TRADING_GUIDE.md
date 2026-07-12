# Paper Trading Guide

Use deterministic fixture or replay data by default. A session validates market
data, runs five specialists, weights evidence, obtains a recommendation, applies
the Risk Manager veto, proposes a local order, simulates fees/slippage, persists
the audit trail, and returns health state.

`paper_execution_eligible` is necessary but never sufficient without current
Risk Manager approval. Simulated cash, size, and price checks can still reject a
proposal. Short simulation is rejected. No Binance.US or other exchange is used.
Entry, mark, and close prices must be finite and positive; invalid marks are
rejected without mutating the simulated position or account.

Artificial replay profit is test output, not a profitability claim. Learning
output is a proposal requiring human approval and never changes production rules.
