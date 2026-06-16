from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReportSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReportCategory(str, Enum):
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    RESOURCE = "resource"
    INTEGRITY = "integrity"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"


@dataclass
class DiagnosticReport:
    detector: str
    severity: ReportSeverity
    category: ReportCategory
    trace_id: str | None = None
    span_id: str | None = None
    location: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "severity": self.severity.value,
            "category": self.category.value,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "location": self.location,
            "message": self.message,
            "details": self.details,
            "recommendation": self.recommendation,
        }
