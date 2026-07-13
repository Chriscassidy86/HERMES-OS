# PAPER Trade Report Cards

Every completed, Risk-approved PAPER trade may produce an immutable version-1 report
card. It records UTC entry/exit facts, gross and net P&L, costs, regimes, thesis,
specialists, evidence, assumptions, uncertainty, calibration, learning suggestions,
and public-provider attribution. Missing entry evidence or Risk approval fails closed.

Cards are stored in `trade_report_cards` by unique trade ID. Duplicates are rejected.
They make no profitability claim and cannot mutate any Hermes configuration.
