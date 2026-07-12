# HERMES-OS Architecture

Foundation II supplies configuration, logging, events, registry, scheduler, and
boot orchestration. Foundation III supplies frozen domain records, the
`BaseSpecialist` contract, Trend specialist, evidence aggregation,
recommendations, risk review, and briefing.

Foundation IV.1 adds `DecisionCycle` as the application boundary:

`MarketSnapshot -> Specialists -> DecisionPacket -> EvidenceSummary -> Recommendation -> RiskAssessment -> DecisionCycleResult`

It validates the snapshot and specialist responses, then returns an immutable
result containing every intermediate decision, cycle identity, final status,
rejection reasons, and paper eligibility. Exceptions, malformed outputs, empty
signals, invalid evidence, WAIT recommendations, and risk rejection fail closed.

The cycle has no exchange adapter, order model, execution service, live-data
connection, or persistent portfolio.

Foundation IV.2 makes the intelligence layer multi-specialist. Trend, Market
Regime, Momentum, Volume, and Volatility produce timestamped evidence using the
same immutable snapshot. `EvidenceAnalyzer` applies explicit specialist weight,
source reliability, confidence, strength, freshness, and timeframe compatibility.
Neutral evidence is recorded but excluded from directional confidence. The
summary exposes contributions, conflicts, exclusions, directional score, and
final confidence so every recommendation remains explainable.

Foundation IV.3 adds an in-memory `PaperPortfolio` aggregate and immutable
account, position, order, fill, trade, and transition records. A proposal must
carry directional cycle eligibility and Risk Manager approval. Deterministic
market fills apply configured fees and slippage, update cash and exposure, and
record every state transition. Short selling is rejected until its accounting
and margin model can be proven safe. No exchange interface exists.
