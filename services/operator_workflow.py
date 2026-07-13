"""Local-only alert detection and PAPER daily workflow services."""

from dataclasses import replace
from datetime import datetime, timezone

from core.research.provenance import stable_checksum
from models.operator_workflow import (
    DailyWorkflowReport,
    OperatorAlert,
    WorkflowStep,
)


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "INFO": 3}
WORKFLOW_LABELS = (
    "confirm PAPER mode",
    "check system health",
    "verify providers",
    "verify database",
    "review latest briefing",
    "review risk state",
    "review open positions",
    "review alerts",
    "run optional replay/research",
    "create backup",
    "verify backup",
    "generate end-of-day report",
)


class LocalAlertManager:
    def __init__(self):
        self._alerts = {}

    def create(self, *, category, severity, message, created_at):
        if severity not in SEVERITY_ORDER or not category.strip() or not message.strip():
            raise ValueError("Alert fields are invalid.")
        created_at = self._utc(created_at)
        alert_id = "ALERT-" + stable_checksum((category, severity, message))[:16]
        existing = self._alerts.get(alert_id)
        if existing is not None and not existing.acknowledged:
            return existing
        alert = OperatorAlert(alert_id, category, severity, message, created_at)
        self._alerts[alert_id] = alert
        return alert

    def acknowledge(self, alert_id, *, acknowledged_at):
        alert = self._alerts[alert_id]
        if alert.acknowledged:
            return alert
        updated = replace(
            alert,
            acknowledged=True,
            acknowledged_at=self._utc(acknowledged_at),
        )
        self._alerts[alert_id] = updated
        return updated

    def alerts(self):
        return tuple(sorted(self._alerts.values(), key=lambda item: (SEVERITY_ORDER[item.severity], item.created_at, item.alert_id)))

    @staticmethod
    def _utc(value):
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Alert timestamps must be timezone-aware.")
        return value.astimezone(timezone.utc)


class OperationalAlertDetector:
    """Maps explicit health facts to alerts; it performs no external I/O."""

    RULES = (
        ("STALE_MARKET_DATA", "HIGH", "market_data_stale", "Market data is stale."),
        ("PROVIDER_UNAVAILABLE", "HIGH", "provider_unavailable", "A market-data provider is unavailable."),
        ("DATABASE_UNHEALTHY", "CRITICAL", "database_unhealthy", "The database is unhealthy."),
        ("LOW_DISK", "HIGH", "low_disk_space", "Available disk space is low."),
        ("HIGH_MEMORY", "WARNING", "high_memory_use", "Memory use is high."),
        ("PAPER_SESSION_FAILURES", "HIGH", "repeated_paper_failures", "Paper sessions are failing repeatedly."),
        ("CIRCUIT_BREAKER", "CRITICAL", "circuit_breaker_triggered", "The circuit breaker is triggered."),
        ("UNUSUAL_DRAWDOWN", "HIGH", "unusual_drawdown", "Paper portfolio drawdown is unusual."),
        ("POSITION_CONCENTRATION", "WARNING", "position_concentration", "Paper position concentration is elevated."),
        ("BACKUP_REJECTED", "HIGH", "backup_rejected", "A backup was rejected."),
        ("RESTORE_VERIFICATION_FAILED", "CRITICAL", "restore_verification_failed", "Restore verification failed."),
        ("MISSING_BRIEFING", "WARNING", "missing_briefing", "The latest executive briefing is missing."),
        ("MISSING_RESEARCH_ARTIFACT", "WARNING", "missing_research_artifact", "A required research artifact is missing."),
        ("CALIBRATION_DEGRADATION", "WARNING", "calibration_degradation", "Confidence calibration has degraded."),
        ("EXPERIMENT_AWAITING_APPROVAL", "INFO", "experiment_awaiting_approval", "A research experiment awaits human approval."),
    )

    def evaluate(self, facts, *, observed_at, manager):
        if not isinstance(manager, LocalAlertManager):
            raise ValueError("A local alert manager is required.")
        return tuple(
            manager.create(category=category, severity=severity, message=message, created_at=observed_at)
            for category, severity, key, message in self.RULES
            if facts.get(key) is True
        )


class DailyOperatorWorkflow:
    def __init__(self):
        self._steps = tuple(WorkflowStep(index, label) for index, label in enumerate(WORKFLOW_LABELS, 1))

    def complete(self, number, *, completed_at):
        if number < 1 or number > len(self._steps):
            raise ValueError("Workflow step number is invalid.")
        completed_at = LocalAlertManager._utc(completed_at)
        self._steps = tuple(replace(step, completed=True, completed_at=completed_at) if step.number == number else step for step in self._steps)
        return self.report()

    def report(self):
        missing = tuple(step.label for step in self._steps if not step.completed)
        return DailyWorkflowReport("PAPER", self._steps, not missing, missing)


class FutureNotificationAdapter:
    enabled = False

    def send(self, _alert):
        raise RuntimeError("External notifications are disabled; local alerts only.")
