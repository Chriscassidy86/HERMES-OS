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

The first adapter release derives price trend, relative volume, volatility
context, momentum, enabled-symbol breadth, and provider agreement from snapshots
already validated by Hermes. Deterministic parsers exist for Fear and Greed and
CoinGecko-shaped fixtures, but their production sources remain disabled pending
current access and terms review. Derivatives remain fixture-only; on-chain and
analyst/community evidence accept bounded, attributed manual imports only.

No source record stores secrets. Unsupported websites, private APIs, paywalls,
CAPTCHAs, robots restrictions, or rate limits are never bypassed.
