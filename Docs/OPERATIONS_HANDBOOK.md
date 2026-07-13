# Operations Handbook

Hermes RC1 runs in PAPER MODE ONLY. Start with `python main.py`; run a complete
fixture session with `python examples/paper_session_demo.py`. Before operation,
run `python scripts/healthcheck.py` and `python -m unittest discover -s tests -v`.

Initialize a journal with `python -m database.cli data/hermes.sqlite3 init`.
Inspect status using `python -m reports.operator_cli data/hermes.sqlite3 status`.
Other reports are `cycle`, `evidence`, `portfolio`, `positions`, `trades`, `pnl`,
`rejections`, `risk`, `provider`, and read-only `integrity`.

On application restart, restore the latest portfolio snapshot before running a
new paper session. Restoration includes order/fill/trade lifecycle history and
continues trade identifiers without reusing persisted IDs.

Logs are rotating structured JSON. Stop cleanly before maintenance. Back up and
restore only with the validated functions in `database.maintenance`. Preserve
the database and logs during incidents; never insert credentials into either.

CLI maintenance: `python -m database.maintenance backup SOURCE DESTINATION` and
`python -m database.maintenance restore BACKUP TARGET`. Stop Hermes before restore.
Run `python -m database.maintenance verify DATABASE` for schema, SQLite quick-check,
and foreign-key verification. Backups are verified against source table row counts.

`PaperOperationsService` validates the journal and restores the latest portfolio
before its first batch. It runs synchronously in the foreground, respects graceful
shutdown, keeps bounded aggregate status counts, and stops after the configured
number of consecutive fully failed batches. Operators must investigate before restart.

## V3.6 research provenance

Research persistence is separate from operational audit tables and is initialized
explicitly through `ResearchRepository.initialize()`. Catalog datasets before a run,
verify their checksums on every rerun, and preserve exported stable JSON plus its
checksum. Conflicting run identifiers fail closed. Do not put credentials, private
keys, passwords, or access tokens in research metadata; secret-shaped fields are rejected.

Run the six V3.6 examples listed in `README.md` for offline workflows. To view an
existing operational journal, run `python scripts/read_only_dashboard.py DATABASE`.
The server binds only to `127.0.0.1`, supports GET dashboard/health routes, exposes
no order or configuration controls, and should be stopped before journal maintenance.
