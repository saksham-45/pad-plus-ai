"""
📋 DiagnosticReport — единый формат результата диагностики.
"""

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
    STABILITY = "stability"


@dataclass
class DiagnosticReport:
    detector: str
    severity: ReportSeverity
    category: ReportCategory
    message: str = ""
    recommendation: str = ""
    status: str = "detected"
    old_value: Any = None
    new_value: Any = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "recommendation": self.recommendation,
            "status": self.status,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
            "timestamp": self.timestamp,
        }
