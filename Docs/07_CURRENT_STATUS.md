# Current Status

Foundation IV.2 is an in-memory, synchronous, paper-only multi-specialist slice. Run
`python examples/workflows/morning_meeting.py` and test with
`python -m unittest discover -s tests -v`.

Paper eligibility is informational. No order is created or placed. Live trading,
exchange connections, API keys, persistent portfolio state, and paper-order
simulation are absent by design.

Evidence is deterministic and explainable but uses initial static weights. Those
weights cannot be changed automatically and are not yet informed by scorecards.
