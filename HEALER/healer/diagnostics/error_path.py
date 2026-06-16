from __future__ import annotations

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace
from aethon.xray.span import Span

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector


class ErrorPathDetector(BaseDetector):
    """Находит spans со статусом 'error' и проверяет, есть ли recovery/fallback.

    Если error-спан не имеет sibling или parent-обработчика ошибки,
    считается, что путь ошибки не обработан."""

    RECOVERY_LIKE_STATUSES = {"ok", "fallback"}

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for trace in store.get_completed_traces():
            reports.extend(self._analyze_trace(trace))
        for trace in store.get_active_traces():
            reports.extend(self._analyze_trace(trace))
        return reports

    def _analyze_trace(self, trace: Trace) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        error_spans = [s for s in trace.spans if s.status == "error"]
        if not error_spans:
            return reports

        span_map: dict[str, Span] = {s.span_id: s for s in trace.spans}
        children_of: dict[str, list[Span]] = {}
        for s in trace.spans:
            pid = s.parent_span_id or ""
            children_of.setdefault(pid, []).append(s)

        for err in error_spans:
            has_recovery = self._check_recovery(err, span_map, children_of)
            if not has_recovery:
                reports.append(DiagnosticReport(
                    detector="error_path",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.CORRECTNESS,
                    trace_id=trace.trace_id,
                    span_id=err.span_id,
                    location=f"span {err.name} ({err.span_id})",
                    message=f"Ошибка в {err.name} без обработчика/fallback",
                    details={
                        "error_span_id": err.span_id,
                        "error_name": err.name,
                        "error_kind": err.kind,
                        "trace_status": trace.status,
                        "trace_name": trace.name,
                    },
                    recommendation="Добавить try/except с fallback или retry-логику",
                ))

        if trace.status == "error":
            reports.append(DiagnosticReport(
                detector="error_path",
                severity=ReportSeverity.ERROR,
                category=ReportCategory.CORRECTNESS,
                trace_id=trace.trace_id,
                location=f"trace {trace.trace_id}",
                message=f"Trace {trace.name} завершился с ошибкой",
                details={
                    "trace_name": trace.name,
                    "trace_status": trace.status,
                    "error_count": len(error_spans),
                    "error_spans": [
                        {"span_id": s.span_id, "name": s.name, "kind": s.kind}
                        for s in error_spans
                    ],
                },
                recommendation="Проверить корневую причину ошибки в spans со статусом 'error'",
            ))

        if trace.status == "ok" and error_spans:
            has_fallback = any(
                s.status == "ok" and s.kind in {"fallback", "provider_fallback"}
                for s in trace.spans
            )
            if has_fallback:
                reports.append(DiagnosticReport(
                    detector="error_path",
                    severity=ReportSeverity.INFO,
                    category=ReportCategory.CORRECTNESS,
                    trace_id=trace.trace_id,
                    location=f"trace {trace.trace_id}",
                    message=f"Trace восстановлен через fallback после {len(error_spans)} ошибок",
                    details={
                        "trace_name": trace.name,
                        "error_count": len(error_spans),
                        "has_fallback": True,
                    },
                    recommendation="Убедиться, что fallback-механизм работает корректно",
                ))

        return reports

    def _check_recovery(
        self,
        error_span: Span,
        span_map: dict[str, Span],
        children_of: dict[str, list[Span]],
    ) -> bool:
        parent_id = error_span.parent_span_id
        if parent_id:
            parent = span_map.get(parent_id)
            if parent and parent.status in self.RECOVERY_LIKE_STATUSES:
                siblings = children_of.get(parent_id, [])
                for sib in siblings:
                    if sib.span_id != error_span.span_id and sib.status in self.RECOVERY_LIKE_STATUSES:
                        return True

        children = children_of.get(error_span.span_id, [])
        for child in children:
            if child.status in self.RECOVERY_LIKE_STATUSES:
                return True

        return False
