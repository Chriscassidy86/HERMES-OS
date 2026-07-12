# Current Status

Hermes OS is at Paper Trading RC1 candidate status. It provides a synchronous,
paper-only multi-specialist decision, simulation, persistence, reporting,
learning-proposal, replay, health, backup, and container stack. Run
`python examples/workflows/morning_meeting.py` and test with
`python -m unittest discover -s tests -v`.

Paper eligibility is informational. No order is created or placed. Live trading,
exchange connections, API keys, persistent portfolio state, and paper-order
simulation are absent by design.

No authenticated exchange client, private API, funded-account connection,
withdrawal capability, or live order path exists. RC1 is long-only for simulated
positions because margin-safe short accounting is intentionally deferred.

Evidence is deterministic and explainable but uses initial static weights. Those
weights cannot be changed automatically and are not yet informed by scorecards.
