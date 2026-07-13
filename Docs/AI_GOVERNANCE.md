# AI Governance

AI output is advisory evidence. It may explain observations, classify text, score
bounded inputs, and propose research changes. Deterministic validation, evidence
aggregation, accounting, and Risk Manager decisions remain authoritative.

AI cannot place or approve an order, bypass a veto, change risk limits, update
weights, write production configuration, conceal excluded evidence, or approve its
own recommendation. Proposals include evidence, sample size, benefit, risks,
before/after estimates, and `human_approval_required=true`. Invalid output fails
independently and closes the affected path.
