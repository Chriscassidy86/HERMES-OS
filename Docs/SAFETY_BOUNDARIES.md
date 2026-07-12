# Safety Boundaries

- PAPER mode is the only accepted runtime mode; live settings raise an error.
- No private exchange API, authenticated client, key input, or order endpoint exists.
- Risk Manager veto always prevents eligibility and simulated execution.
- Missing, stale, malformed, contradictory, or failed evidence closes the cycle.
- Public data is optional, read-only, credential-free, and injected.
- Learning never writes configuration or risk rules.
- Operator reports are read-only; containers expose no trading port or control.
- Short selling, margin, withdrawals, and funded accounts are unsupported.

Any future live adapter requires a separate architecture, security review,
credential boundary, reconciliation model, kill switch, and explicit approval.
It must not be added to this release line.
