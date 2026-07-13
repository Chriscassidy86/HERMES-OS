# Hermes PAPER Launch Guide (Windows PowerShell)

Hermes uses fake money only. It has no authenticated exchange client and cannot send a real order.

Open PowerShell and run:

```powershell
Set-Location 'D:\Desktop\HERMES-OS'
.\scripts\hermes.ps1 start
.\scripts\hermes.ps1 status
.\scripts\hermes.ps1 health
.\scripts\hermes.ps1 dashboard
```

The dashboard is [http://127.0.0.1:8765/](http://127.0.0.1:8765/) and is published on host loopback only. Look for `PAPER MODE ONLY` before trusting the display.

Operational commands:

```powershell
.\scripts\hermes.ps1 logs
.\scripts\hermes.ps1 portfolio
.\scripts\hermes.ps1 trades
.\scripts\hermes.ps1 provider
.\scripts\hermes.ps1 alerts
.\scripts\hermes.ps1 backup
.\scripts\hermes.ps1 verify-backup
.\scripts\hermes.ps1 restart
.\scripts\hermes.ps1 stop
```

`stop` performs a graceful Compose shutdown. `restart` preserves the named data volume and restores the latest shared PAPER portfolio before scheduling resumes.

Defaults: BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT; 4H public candles; 30-second cycles; Binance.US then Coinbase then Kraken; $10,000 fake starting cash; 10 basis-point fees; 5 basis-point slippage. Risk Manager permits directional recommendations at 70% confidence or higher, caps simulated notional at $20 or $25, and rejects invalid, non-directional, low-confidence, stale, future, malformed, contradictory or unsupported evidence.

Data is `/app/data/hermes.sqlite3` in volume `hermes-os_hermes-data`. The verified backup is `/app/data/hermes-backup.sqlite3`. Use `docker compose logs` through the operator script for runtime logs; `hermes-os_hermes-logs` is reserved for structured file logs.
