# SQLite Audit Journal

Foundation IV.4 uses schema version 1 with tables for decision cycles,
snapshots, specialist reports, evidence summaries, recommendations, risk
assessments, paper orders, fills, positions, trades, portfolio snapshots, and
rejection reasons. Payloads use deterministic sorted JSON and UTC timestamps.

Initialize with `python -m database.cli data/hermes.sqlite3 init`. Inspect with
the `cycles`, `trades`, `portfolio`, or `rejections` command. Writes are
transactional, cycle IDs are unique, and imports never initialize a database.
