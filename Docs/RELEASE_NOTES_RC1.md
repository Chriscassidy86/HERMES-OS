# Hermes OS Paper Trading RC1

RC1 is a local Python paper-trading research operating system with five
deterministic specialists, weighted explainable evidence, Risk Manager veto,
long-only simulated execution, SQLite audit journal, replay, performance and
human-review learning proposals, operator JSON reports, healthchecks, backups,
Docker paper service, and CI.

Limitations: static initial specialist weights; simple deterministic heuristics;
fixed demonstration risk caps; no safe short/margin model; no authenticated or
default internet provider; synchronous single-process operation; SQLite local
storage; artificial replay fixtures; no claim of profitability; no live trading.

Upgrade requires schema/test review, backup, full suite, replay smoke test, and
paper session smoke test. Never reuse this RC as a live execution service.

## Local release audit

The full 89-test suite, healthcheck, formatting/compile checks, fresh install,
schema/backup tests, paper session, replay, standard-library dependency inventory,
and forbidden private-exchange capability scan passed on 2026-07-12. Docker CLI
29.5.3 was present, but the local Linux Docker daemon was not running, so the
image build could not execute (`dockerDesktopLinuxEngine` pipe missing). Manifest
structure, non-root user, PAPER environment, and healthcheck are test-covered.

The final audit also verified the replay summary exposes total return, win/loss,
drawdown, profit factor, expectancy, holding time, trade/rejection/no-trade
counts, and specialist accuracy, and that backup/restore are callable commands.
