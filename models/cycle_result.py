"""Immutable result produced by one paper-only Hermes decision cycle."""

from dataclasses import dataclass
from datetime import datetime

from models.decision_packet import DecisionPacket
from models.evidence_summary import EvidenceSummary
from models.recommendation import Recommendation
from models.risk_assessment import RiskAssessment
from reports.agent_report import AgentReport
from reports.market_snapshot import MarketSnapshot


@dataclass(frozen=True)
class DecisionCycleResult:
    cycle_id: str
    timestamp: datetime
    snapshot: MarketSnapshot
    specialist_reports: tuple[AgentReport, ...]
    decision_packet: DecisionPacket
    evidence_summary: EvidenceSummary
    recommendation: Recommendation
    risk_assessment: RiskAssessment
    final_status: str
    rejection_reasons: tuple[str, ...]
    paper_execution_eligible: bool

