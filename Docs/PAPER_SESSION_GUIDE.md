# First Operator-Observed PAPER Session

1. Start Hermes using `Docs/LAUNCH_GUIDE.md`.
2. Confirm both services are healthy and the dashboard says PAPER MODE ONLY.
3. Review provider attribution, Risk result, fake cash/equity, positions and recent decisions.
   The page refreshes every five seconds; a red refresh warning retains the last
   known values and means the operator should check service health.
4. Leave the session running while observing `hermes.ps1 logs` and refreshing operator reports.
5. Do not force trades. WAIT and Risk rejection are valid outcomes.
6. Back up and verify the journal before maintenance.
7. Stop with `hermes.ps1 stop`.
8. Start again and confirm cash, positions, fills and trades match the pre-stop state.

Portfolio snapshots, decisions, fills, positions, trades and dashboard history survive restart in SQLite. Scheduler counters, provider cooldown counters, learning-loop memory and alert acknowledgement are process-local and restart empty. Persisted rejection history remains available through `hermes.ps1 alerts`.

Public observations carry their source and original candle timestamp. The current launch uses no API key, authenticated request, private endpoint, withdrawal or real-order transport. Results are experimental and make no profitability claim.

The dashboard is display-only. It has no order, strategy, weight, risk-limit, or
configuration controls. Raw projection data is available at `/api/dashboard` for
debugging; never interpret `WAIT` or Risk rejection as a service failure by itself.

After completed trades accumulate, inspect `report`, `scoreboard`, `decisions`, and
`summary`. Report cards retain the thesis, risk approval, evidence, provider, costs,
outcome, calibration, and limitations. Decision outcomes use later observations and
must never be described as information available to the original live PAPER cycle.
