# Market Consensus Intelligence

Market Consensus Intelligence is an independent, advisory evidence layer. It
describes what governed outside public evidence suggests; it does not recommend
or execute trades and cannot change Hermes specialists, confidence, Risk Manager
decisions, order sizing, or portfolio state.

## Domain boundary

Consensus observations are immutable, checksum-attributed records with explicit
symbol, timeframe, UTC observation and ingestion times, normalized non-executable
direction, confidence, strength, uncertainty, reliability, trust, provenance,
limitations, warnings, and eligibility. Exact duplicate observations are
deduplicated while conflicting duplicates fail closed. Stale or otherwise
ineligible evidence must retain an exclusion reason.

Outside evidence uses bullish, bearish, neutral, or unknown observation labels.
It never overloads BUY or SELL. Public popularity does not establish correctness,
fixtures and limited PAPER results do not prove profitability, and inaccessible
sources remain disabled until a permitted machine-readable access method exists.

M2 adds a governed registry whose sources are inactive by default. Explicit
configuration may activate only implemented public, fixture, or import adapters;
unavailable, deferred, and unconfigured licensed sources fail closed.

M3 adapters use injected transports, bounded retries, UTC and freshness checks,
health records, and deterministic fixtures. They expose no credential, private
endpoint, HTML scraping, order, or withdrawal interface.
