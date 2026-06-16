from __future__ import annotations

from aethon.xray.trace_store import store
from aethon.xray.causal_validator import (
    validate_trace_causal_integrity,
    detect_orphan_over_time,
)
from aethon.xray.trace import Trace

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector

SEVERITY_MAP = {
    "error": ReportSeverity.ERROR,
    "warning": ReportSeverity.WARNING,
    "info": ReportSeverity.INFO,
}


class CausalViolationDetector(BaseDetector):
    """Обёртка над causal_validator из X-RAY kernel.

    Преобразует результаты проверок causal_validator в DiagnosticReport."""

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        for trace in store.get_completed_traces():
            reports.extend(self._analyze_trace(trace))
        for trace in store.get_active_traces():
            reports.extend(self._analyze_trace(trace))

        reports.extend(self._check_orphans())

        return reports

    def _analyze_trace(self, trace: Trace) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        result = validate_trace_causal_integrity(trace)

        if result["causal_integrity"] == "ok":
            return reports

        for v in result["violations"]:
            severity = SEVERITY_MAP.get(v.get("severity", "warning"), ReportSeverity.WARNING)
            reports.append(DiagnosticReport(
                detector="causal_violation",
                severity=severity,
                category=ReportCategory.INTEGRITY,
                trace_id=trace.trace_id,
                span_id=v.get("span_id"),
                location=f"trace {trace.name} ({trace.trace_id})",
                message=v.get("detail", v.get("type", "causal violation")),
                details={
                    "violation_type": v.get("type"),
                    "violation_severity": v.get("severity"),
                    "span_id": v.get("span_id"),
                    "parent_span_id": v.get("parent_span_id"),
                    "trace_name": trace.name,
                },
                recommendation=self._recommendation_for(v.get("type", "")),
            ))

        return reports

    def _check_orphans(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        try:
            all_traces = store.get_completed_traces() + store.get_active_traces()
            orphan_violations = detect_orphan_over_time(all_traces, store)

            for v in orphan_violations:
                severity = SEVERITY_MAP.get(v.get("severity", "warning"), ReportSeverity.WARNING)
                reports.append(DiagnosticReport(
                    detector="causal_violation",
                    severity=severity,
                    category=ReportCategory.INTEGRITY,
                    trace_id=v.get("trace_id"),
                    span_id=v.get("span_id"),
                    location="orphan spans",
                    message=v.get("detail", "orphan span detected"),
                    details={
                        "violation_type": v.get("type"),
                        "span_id": v.get("span_id"),
                        "trace_id": v.get("trace_id"),
                        "name": v.get("name"),
                        "age_s": v.get("age_s"),
                    },
                    recommendation="Проверить, что span регистрируется в активном trace, "
                                   "или создать trace до создания span",
                ))
        except Exception:
            pass

        return reports

    @staticmethod
    def _recommendation_for(violation_type: str) -> str:
        recs = {
            "child_before_parent": "Убедиться, что parent span создаётся до child span",
            "child_outlives_parent": "Завершать child spans до parent span",
            "span_ends_after_freeze": "Не создавать spans после trace.end()",
            "late_span_after_freeze": "Не создавать spans после freeze",
            "confirmed_orphan": "Создавать trace до span, или регистрировать span в trace",
            "logical_clock_regression": "Проверить logical_ts: родитель должен быть меньше child",
            "logical_clock_non_monotonic": "Проверить монотонность logical_ts",
        }
        return recs.get(violation_type, "Проверить causal integrity trace")
