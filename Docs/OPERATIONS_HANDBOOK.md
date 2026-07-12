# Operations Handbook

Hermes RC1 runs in PAPER MODE ONLY. Start with `python main.py`; run a complete
fixture session with `python examples/paper_session_demo.py`. Before operation,
run `python scripts/healthcheck.py` and `python -m unittest discover -s tests -v`.

Initialize a journal with `python -m database.cli data/hermes.sqlite3 init`.
Inspect status using `python -m reports.operator_cli data/hermes.sqlite3 status`.
Other reports are `cycle`, `evidence`, `portfolio`, `positions`, `trades`, `pnl`,
`rejections`, `risk`, and `provider`.

Logs are rotating structured JSON. Stop cleanly before maintenance. Back up and
restore only with the validated functions in `database.maintenance`. Preserve
the database and logs during incidents; never insert credentials into either.
