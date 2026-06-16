from __future__ import annotations

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector

SLOW_IMPORT_THRESHOLD_MS = 100.0
IMPORT_LIKE_KINDS = {"import", "module_load", "init", "setup"}
IMPORT_LIKE_NAMES = ("import", "load", "init", "setup", "bootstrap")


class SlowImportDetector(BaseDetector):
    """Находит медленные импорты и инициализацию модулей в трейсах.

    Анализирует spans, чей kind или name похож на загрузку модуля,
    и сообщает о тех, что превышают порог длительности."""

    def __init__(self, threshold_ms: float = SLOW_IMPORT_THRESHOLD_MS):
        self.threshold_ms = threshold_ms

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for trace in store.get_completed_traces():
            reports.extend(self._analyze_trace(trace))
        for trace in store.get_active_traces():
            reports.extend(self._analyze_trace(trace))
        return reports

    def _analyze_trace(self, trace: Trace) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for span in trace.spans:
            if span.duration_ms is None:
                continue
            if not self._is_import_like(span):
                continue
            if span.duration_ms > self.threshold_ms:
                reports.append(DiagnosticReport(
                    detector="slow_import",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.PERFORMANCE,
                    trace_id=trace.trace_id,
                    span_id=span.span_id,
                    location=f"span {span.name} ({span.span_id})",
                    message=f"Медленная инициализация: {span.name} — {span.duration_ms:.1f}ms "
                            f"(порог {self.threshold_ms}ms)",
                    details={
                        "span_name": span.name,
                        "span_kind": span.kind,
                        "duration_ms": span.duration_ms,
                        "threshold_ms": self.threshold_ms,
                        "trace_name": trace.name,
                    },
                    recommendation="Перенести импорт внутрь функции (lazy import) или "
                                   "использовать отложенную инициализацию",
                ))
        return reports

    @staticmethod
    def _is_import_like(span) -> bool:
        if span.kind in IMPORT_LIKE_KINDS:
            return True
        name_lower = span.name.lower()
        for prefix in IMPORT_LIKE_NAMES:
            if name_lower.startswith(prefix):
                return True
        return False
