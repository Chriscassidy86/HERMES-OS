# Wall-Clock PAPER Soak Guide

Start the normal PAPER platform, verify health, then choose one target:

```powershell
.\scripts\hermes.ps1 soak-start 24h
.\scripts\hermes.ps1 soak-start 72h
.\scripts\hermes.ps1 soak-start 7d
```

Use `soak-status`, `soak-stop`, and `soak-export` to inspect, stop, and export. State
tracks identity, UTC duration, restarts, cycles, failovers, file sizes, RSS when the
platform exposes it, slow cycles, errors, alerts, stop reason, and completion. A second
running soak is rejected. No soak was automatically started by this upgrade.

The exported artifact is PAPER-only evidence and does not prove profitability or live readiness.
Once an operator starts a soak, the running PAPER service updates cycle, provider
failover, error, alert, file-size, RSS, elapsed-time, and restart observations. With no
active soak state the observer is dormant and performs no writes.
