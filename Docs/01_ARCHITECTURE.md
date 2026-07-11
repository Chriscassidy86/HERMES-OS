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
