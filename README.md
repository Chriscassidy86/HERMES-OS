# HERMES-OS

HERMES-OS is an experimental Python multi-agent crypto decision system. The
current release implements Foundation IV.1: a small, synchronous, paper-only
operational decision cycle.

## Implemented architecture

`MarketSnapshot -> Specialists -> DecisionPacket -> EvidenceSummary -> Recommendation -> RiskAssessment -> DecisionCycleResult`

Foundation II provides configuration, logging, events, a registry, a scheduler,
and boot orchestration. Foundation III provides domain models, the Trend
specialist, evidence aggregation, recommendation logic, risk review, and an
executive brief. Foundation IV.1 connects those pieces through `DecisionCycle`.

## Run the decision cycle

```powershell
python examples/workflows/morning_meeting.py
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The project currently uses only the Python standard library.

## Safety boundary

- Paper execution eligibility is a decision flag only; it does not place orders.
- No broker, exchange, API-key, or Binance.US integration exists.
- `LIVE_TRADING` remains `False`.
- Invalid or empty evidence and risk rejection always prevent eligibility.
- Persistent paper portfolios and simulated orders are outside Foundation IV.1.

## Current limitations

- Trend is the only implemented specialist.
- Evidence uses unweighted vote counts and average confidence.
- Risk rules use fixed demonstration limits rather than portfolio state.
- Snapshots are caller-supplied; there is no market-data provider.
- The cycle is synchronous and in-memory, with no persistent audit store.
