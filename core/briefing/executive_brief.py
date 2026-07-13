"""
===============================================================================

Hermes OS

File:
executive_brief.py

Purpose:
Creates a human-readable executive briefing from an EvidenceSummary.

Author:
Hermes Quant Labs

Foundation:
III - Intelligence Layer

===============================================================================
"""

from models.evidence_summary import EvidenceSummary


class ExecutiveBrief:
    """
    Builds CEO-facing briefing text.
    """

    def create(self, summary: EvidenceSummary, explanation=None) -> str:
        explanation_text = ""
        if explanation is not None:
            explanation_text = (
                "\nExplanation\n\n"
                f"{explanation.executive_summary()}\n"
                f"Agrees: {', '.join(explanation.agreeing_specialists) or 'None'}\n"
                f"Disagrees: {', '.join(explanation.disagreeing_specialists) or 'None'}\n"
                f"Ignored: {', '.join(explanation.ignored_reasons) or 'None'}\n"
                f"Uncertainty: {'; '.join(explanation.uncertainties)}\n"
            )
        return f"""
==========================================================
                HERMES QUANT LABS
                 EXECUTIVE BRIEF
==========================================================

Market

{summary.symbol}

----------------------------------------------------------

Evidence Summary

Bullish Departments : {summary.bullish}
Bearish Departments : {summary.bearish}
Neutral Departments : {summary.neutral}

Average Confidence  : {summary.average_confidence}%
Signal Count        : {summary.signal_count}
{explanation_text}

----------------------------------------------------------

Status

CONTINUE MONITORING

==========================================================
"""
