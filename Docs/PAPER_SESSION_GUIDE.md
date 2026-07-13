# First Operator-Observed PAPER Session

1. Start Hermes using `Docs/LAUNCH_GUIDE.md`.
2. Confirm both services are healthy and the dashboard says PAPER MODE ONLY.
3. Review provider attribution, Risk result, fake cash/equity, positions and recent decisions.
4. Leave the session running while observing `hermes.ps1 logs` and refreshing operator reports.
5. Do not force trades. WAIT and Risk rejection are valid outcomes.
6. Back up and verify the journal before maintenance.
7. Stop with `hermes.ps1 stop`.
8. Start again and confirm cash, positions, fills and trades match the pre-stop state.

Portfolio snapshots, decisions, fills, positions, trades and dashboard history survive restart in SQLite. Scheduler counters, provider cooldown counters, learning-loop memory and alert acknowledgement are process-local and restart empty. Persisted rejection history remains available through `hermes.ps1 alerts`.

Public observations carry their source and original candle timestamp. The current launch uses no API key, authenticated request, private endpoint, withdrawal or real-order transport. Results are experimental and make no profitability claim.
