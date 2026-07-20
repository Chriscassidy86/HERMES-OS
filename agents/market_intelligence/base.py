"""
===============================================================================

Hermes OS

File:
base.py

Purpose:
Abstract base class for all Market Intelligence specialists.

This interface defines the contract that future intelligence agents will
inherit. It enforces advisory-only behavior, deterministic metadata, and
health-check support. No specialist in this framework may produce buy/sell
actions, create orders, mutate portfolios, or access exchanges.

Author:
Hermes Quant Labs

Foundation:
VIII - Market Intelligence Framework

===============================================================================
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from models.market_intelligence import (
    AgentStatus,
    HealthCheckResult,
    MarketIntelligenceContext,
    MarketIntelligenceReport,
    SpecialistMetadata,
)


class MarketIntelligenceSpecialist(ABC):
    """
    Abstract base class for all Market Intelligence specialists.

    Every specialist must:
      - declare a name, version, status, supported symbols, and timeframes
      - implement ``analyze`` to produce an advisory-only report
      - implement ``health_check`` to report operational status
      - implement ``metadata`` to return complete specialist metadata

    Specialists must NOT:
      - produce buy/sell actions or order directives
      - mutate portfolios or Risk Manager state
      - access exchanges, APIs, or network resources
      - bypass advisory-only enforcement

    The base class provides default implementations for ``metadata`` and
    ``health_check`` that subclasses may override. The defaults ensure
    that even a minimal specialist produces valid, advisory-only output.
    """

    #: Semantic version of the specialist implementation.
    VERSION: str = "0.1.0"

    #: Symbols supported by default; subclasses should override.
    SUPPORTED_SYMBOLS: tuple[str, ...] = ()

    #: Timeframes supported by default; subclasses should override.
    SUPPORTED_TIMEFRAMES: tuple[str, ...] = ()

    def __init__(self, name: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Specialist name is required.")
        self._name = name
        self._status: AgentStatus = AgentStatus.STARTING

    # -- Properties ----------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the specialist name."""
        return self._name

    @property
    def version(self) -> str:
        """Return the specialist version."""
        return self.VERSION

    @property
    def status(self) -> AgentStatus:
        """Return the current operational status."""
        return self._status

    @property
    def supported_symbols(self) -> tuple[str, ...]:
        """Return the tuple of supported symbols."""
        return self.SUPPORTED_SYMBOLS

    @property
    def supported_timeframes(self) -> tuple[str, ...]:
        """Return the tuple of supported timeframes."""
        return self.SUPPORTED_TIMEFRAMES

    # -- Abstract methods ----------------------------------------------------

    @abstractmethod
    def analyze(self, context: MarketIntelligenceContext) -> MarketIntelligenceReport:
        """
        Analyze the given context and produce an advisory-only report.

        Subclasses must implement this method to produce a
        ``MarketIntelligenceReport`` with validated evidence, confidence,
        and explanation. The report must never contain buy/sell actions.

        Args:
            context: Validated market intelligence context with symbol,
                timeframe, and UTC-aware observed_at timestamp.

        Returns:
            An immutable, advisory-only ``MarketIntelligenceReport``.

        Raises:
            ValueError: If inputs are invalid, stale, or future-dated.
        """
        raise NotImplementedError

    # -- Default implementations --------------------------------------------

    def health_check(self, now: datetime | None = None) -> HealthCheckResult:
        """
        Return a health check result for this specialist.

        The default implementation reports the current status. Subclasses
        may override to perform additional checks (e.g., data availability).

        Args:
            now: Optional injected clock for deterministic testing.

        Returns:
            An immutable ``HealthCheckResult``.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        healthy = self._status in (AgentStatus.ONLINE, AgentStatus.DEGRADED)
        if self._status == AgentStatus.ONLINE:
            explanation = "Specialist is online and ready."
        elif self._status == AgentStatus.DEGRADED:
            explanation = "Specialist is degraded but partially operational."
        elif self._status == AgentStatus.STARTING:
            explanation = "Specialist is starting up."
        elif self._status == AgentStatus.OFFLINE:
            explanation = "Specialist is offline."
        else:
            explanation = "Specialist is in an error state."
        return HealthCheckResult(
            agent_name=self._name,
            status=self._status,
            healthy=healthy,
            explanation=explanation,
            checked_at=now,
        )

    def metadata(self) -> SpecialistMetadata:
        """
        Return complete metadata for this specialist.

        Returns:
            An immutable ``SpecialistMetadata`` instance.
        """
        return SpecialistMetadata(
            name=self._name,
            version=self.VERSION,
            status=self._status,
            supported_symbols=self.SUPPORTED_SYMBOLS,
            supported_timeframes=self.SUPPORTED_TIMEFRAMES,
        )

    # -- Status transitions --------------------------------------------------

    def _set_status(self, status: AgentStatus) -> None:
        """Set the operational status. Intended for subclass use."""
        if not isinstance(status, AgentStatus):
            raise ValueError("status must be an AgentStatus.")
        self._status = status
