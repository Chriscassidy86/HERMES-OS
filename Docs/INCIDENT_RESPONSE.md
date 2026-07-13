# Incident Response

1. Stop the paper process or container; do not delete files.
2. Record UTC time, health output, latest cycle ID, and operator status report.
3. Preserve database and rotating logs with a validated backup.
4. If data is stale/malformed, disable the provider and use deterministic fixtures.
5. If accounting invariants or schema checks fail, do not resume paper execution.
6. Reproduce with tests/replay, document cause, and require review before changes.
7. Restore only a schema-validated backup while the process is stopped.
8. If dashboard exposure is suspected, stop the listener, confirm it was bound to `127.0.0.1`, preserve logs, and do not add a public proxy during response.

There is no live-account containment procedure because RC1 cannot connect to one.
