"""Serialization-only CEO dashboard renderer; contains no business logic."""

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json

from models.ceo_dashboard import CEODashboardView


class CEODashboardRenderer:
    def to_dict(self, view: CEODashboardView) -> dict:
        if not isinstance(view, CEODashboardView):
            raise ValueError("A CEO dashboard view is required.")
        return asdict(view)

    def to_json(self, view: CEODashboardView) -> str:
        return json.dumps(self.to_dict(view), default=self._default, indent=2, sort_keys=True)

    @staticmethod
    def _default(value):
        if isinstance(value, Decimal): return str(value)
        if isinstance(value, datetime): return value.isoformat()
        if isinstance(value, Enum): return value.value
        raise TypeError(f"Unsupported CEO dashboard value: {type(value).__name__}")

