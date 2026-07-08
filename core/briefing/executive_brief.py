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

    def create(self, summary: EvidenceSummary) -> str:
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

----------------------------------------------------------

Status

CONTINUE MONITORING

==========================================================
"""