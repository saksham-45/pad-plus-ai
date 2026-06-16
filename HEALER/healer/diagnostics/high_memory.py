from __future__ import annotations

import logging

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector

logger = logging.getLogger("healer.diagnostics.high_memory")

HIGH_MEMORY_THRESHOLD = 90.0
WARN_MEMORY_THRESHOLD = 75.0

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None


class HighMemoryDetector(BaseDetector):
    """Проверяет использование системной памяти.

    Если memory_usage > 90% — critical alert.
    Если > 75% — warning.
    """

    def __init__(self, critical_threshold: float = HIGH_MEMORY_THRESHOLD,
                 warning_threshold: float = WARN_MEMORY_THRESHOLD):
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        if not HAS_PSUTIL:
            reports.append(DiagnosticReport(
                detector="high_memory",
                severity=ReportSeverity.WARNING,
                category=ReportCategory.RESOURCE,
                location="system",
                message="psutil не установлен — мониторинг памяти недоступен",
                recommendation="Установите psutil: pip install psutil",
            ))
            return reports

        memory = psutil.virtual_memory()
        percent = memory.percent

        if percent > self.critical_threshold:
            severity = ReportSeverity.CRITICAL
            message = (
                f"Критическое использование памяти: {percent:.1f}% "
                f"(порог {self.critical_threshold}%)"
            )
            recommendation = (
                "Очистить кэш L1, перезапустить неиспользуемые компоненты, "
                "увеличить объём RAM"
            )
        elif percent > self.warning_threshold:
            severity = ReportSeverity.WARNING
            message = (
                f"Высокое использование памяти: {percent:.1f}% "
                f"(порог {self.warning_threshold}%)"
            )
            recommendation = "Запланировать очистку кэша, проверить утечки памяти"
        else:
            return reports

        reports.append(DiagnosticReport(
            detector="high_memory",
            severity=severity,
            category=ReportCategory.RESOURCE,
            location="system",
            message=message,
            details={
                "memory_percent": percent,
                "memory_used_gb": round(memory.used / (1024 ** 3), 2),
                "memory_total_gb": round(memory.total / (1024 ** 3), 2),
                "critical_threshold": self.critical_threshold,
                "warning_threshold": self.warning_threshold,
            },
            recommendation=recommendation,
        ))

        return reports
