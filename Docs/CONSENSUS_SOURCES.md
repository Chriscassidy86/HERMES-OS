# Consensus Sources

Hermes maintains a deterministic source catalog. Registration does not activate a
source; operators or reviewed application configuration must explicitly list every
enabled source ID.

| Source | Status | Access | Initial state |
|---|---|---|---|
| Hermes validated public market evidence | Public | Existing provider snapshots | Available, disabled until configured |
| Fear and Greed | Unavailable/deferred | Official public endpoint only | Disabled pending access review |
| CoinGecko metadata | Unavailable/deferred | Official documented endpoint only | Disabled pending access review |
| Derivatives | Fixture | Deterministic fixture | Fixture-only |
| On-chain | Export | Manual permitted import | Import-only |
| Analyst/community | Export | Manual permitted import | Import-only; no scraping |
| Licensed on-chain | Licensed | Licensed dataset | Not configured |

No source record stores secrets. Unsupported websites, private APIs, paywalls,
CAPTCHAs, robots restrictions, or rate limits are never bypassed.
