# Foundation Ledger

| Milestone | Purpose | Status | Date | Commit | Tests / acceptance | Limitations |
|---|---|---|---|---|---|---|
| IV.1 | Operational decision cycle | Complete | 2026-07-11 | `8eb6725` | 7 tests; immutable fail-closed result | One specialist at completion |
| IV.2 | Weighted multi-specialist intelligence | Complete | 2026-07-11 | `1afbd60` | 17 tests; five explainable specialists | Static weights |
| IV.3 | Paper portfolio lifecycle | Complete | 2026-07-11 | `7d35cce` | 27 tests; audited fills/accounting | Long-only simulation |
| IV.4 | SQLite audit journal | Complete | 2026-07-11 | `bc54202` | 36 tests; transactions/idempotence | Local SQLite |
| V.1 | Validated market data | Complete | 2026-07-11 | `459a84b` | 44 tests; fixture/replay/read-only boundary | No default network provider |
| V.2 | Orchestrated sessions | Complete | 2026-07-12 | `1593ee9` | 53 tests; failures/duplicates/restart | Synchronous |
| VI | Performance and learning | Complete | 2026-07-12 | `295f950` | 61 tests; config immutability | Proposals need human review |
| VII | Operator reporting | Complete | 2026-07-12 | `1f18906` | 67 tests; read-only JSON reports | No dashboard |
| VIII | Backtest and replay | Complete | 2026-07-12 | `48430a2` | 75 tests; no look-ahead/reproducible | Fixtures are not profitability evidence |
| IX | Paper production hardening | Complete | 2026-07-12 | `71a0c44` | 83 tests; health/backup/container/CI | Single-process SQLite |
| X | Paper RC1 | Complete | 2026-07-12 | `7ac6b8b` | 89 tests plus release audit and smoke tests | PAPER MODE ONLY |
