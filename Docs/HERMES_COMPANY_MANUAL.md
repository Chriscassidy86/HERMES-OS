# Hermes Quant Labs Company Manual

## Mission and vision

Hermes Quant Labs builds Hermes OS: a trustworthy, explainable, paper-first
quantitative research platform. Capital protection and system integrity precede
performance. Results state their source, sample size, costs, limitations, and
drawdown; fixtures and short paper samples never support profitability claims.

## Structure and authority

The CEO owns product and release approval. Engineering owns implementation and
verification. Research proposes hypotheses and configuration changes. Risk
governance defines deterministic limits and may veto any proposal. Operations may
stop a release or paper service when health, auditability, or safety is uncertain.
Only a human may approve releases, migrations, risk-policy changes, model weights,
or production configuration changes.

## Operating philosophy

- Protect capital, preserve integrity, explain decisions, then optimize.
- Prefer deterministic calculations and immutable records.
- Fail closed on missing, stale, future, malformed, contradictory, or untrusted data.
- Keep business rules outside presentation and provider adapters.
- Add tests and documentation with every behavior change.
- Favor simple local operation and low-cost infrastructure until scale is proven.

## Engineering, Git, and documentation

Work branches use `development/*`; features never begin on `main`. Commits are
small, descriptive, tested, and do not rewrite shared history. Releases require a
reviewed pull request, green tests and secret scanning, post-merge verification,
and an annotated tag. Architecture, status, progress, changelog, operator guidance,
and release notes must describe shipped behavior.

## Security and incidents

Secrets never enter Git, images, logs, fixtures, or reports. V2 has no live
trading, authenticated exchange client, private endpoint, withdrawal path, or API
key input. Suspected secret exposure, data corruption, unsafe execution, or audit
loss requires stopping the affected process, preserving evidence, notifying the
CEO and engineering owner, and following `INCIDENT_RESPONSE.md`.

## AI, risk, and research governance

AI may summarize, classify, score, reason, and propose. It may not place orders,
override Risk Manager, silently alter weights or limits, approve its own proposal,
or mutate production configuration. Risk Manager veto is final. Experiments
preserve baselines, distinguish fixture/replay/public observation/paper data,
state uncertainty, and require human approval before adoption.

## Paper/live boundary and operating cost

Hermes OS is PAPER mode only. Live trading requires a separate architecture,
credential boundary, reconciliation model, security review, kill switch, tests,
and explicit human approval; it is prohibited on this release line. Prefer local
SQLite, containers, standard-library services, and a small VPS only when needed.
