# Engineering Standards

Use Python 3.11+, explicit UTC-aware clocks, immutable domain records, `Decimal`
for paper accounting, injected I/O boundaries, and deterministic ordering. Validate
inputs at trust boundaries and preserve exception causes while exposing safe errors.
Close files, database connections, and subprocesses predictably.

Every change requires focused regression tests plus the full suite, compilation,
format checks, `git diff --check`, relevant examples, and documentation updates.
Network tests use fixtures. Concurrency must be explicit; single-process components
must say so. SQLite writes use transactions, foreign keys, schema validation,
backups, and restart tests.

Reviews check correctness, accounting invariants, replay lookahead, timezones,
failure isolation, logging consistency, resources, dead/duplicate code, security
boundaries, and documentation truthfulness. Presentation code is read-only.
