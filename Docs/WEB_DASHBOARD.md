# Web Dashboard

Run `python scripts/read_only_dashboard.py DATABASE --port 8765` or use
`.\scripts\hermes.ps1 dashboard`. Open `http://127.0.0.1:8765/`.

The dark responsive operator view includes system, PAPER, database and provider
health; current regime, recommendation, confidence and Risk Manager result;
portfolio metrics and positions; four enabled symbol cards; specialist inclusion
and exclusion; the complete human decision explanation; provider observations;
bounded recent activity; and local canvas charts for equity, cash, exposure,
drawdown, prices and recommendations. Charts are labeled PAPER/public observation,
use UTC data, show explicit empty states, and make no profitability claim.

The browser requests `GET /api/dashboard` every five seconds. On failure it keeps
the last successful display, shows a warning, and retries. Debugging endpoints are:

- `GET /health`
- `GET /api/dashboard`
- `GET /api/portfolio`
- `GET /api/providers`
- `GET /api/trades`
- `GET /api/alerts`
- `GET /api/specialists`
- `GET /api/report-cards`
- `GET /api/decisions`
- `GET /api/session-summary`
- `GET /api/performance`

`WAIT` or `HOLD` means Hermes has no approved directional action. `REJECTED` means
Risk Manager vetoed a directional recommendation. `DATA STALE` and `PROVIDER FAILURE`
mean the cycle failed closed and require operator investigation.

The application binds directly to `127.0.0.1`. Compose uses an explicit container
bridge while publishing port 8765 to host loopback only. Every route is GET-only;
POST, PUT, PATCH and DELETE return 405. There are no order controls, API-key forms,
live controls, or configuration mutations. All calculations and risk decisions are
performed in Python services before the immutable projection reaches the renderer.

The Paper Validation Intelligence section adds display-only filters for symbol,
recommendation, Risk result, trade result, and specialist. Server-side filters are
allow-listed and invalid keys return HTTP 400. Scoreboards, latest report card,
session summaries, decision-quality metrics, rejection/WAIT quality, and searchable
decision/trade history remain stable JSON projections with bounded results.
