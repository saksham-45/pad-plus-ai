from __future__ import annotations

import time

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector

LEAK_THRESHOLD_S = 30.0
CONNECTION_LIKE_KINDS = {"provider_call", "gateway_request", "memory_access"}


class ResourceLeakDetector(BaseDetector):
    """Находит потенциальные утечки ресурсов: spans без end(),
    которые висят дольше порога, и orphan spans без trace."""

    def __init__(self, leak_threshold_s: float = LEAK_THRESHOLD_S):
        self.leak_threshold_s = leak_threshold_s

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        reports.extend(self._check_unended_spans())
        reports.extend(self._check_orphan_spans())
        reports.extend(self._check_dangling_traces())

        return reports

    def _check_unended_spans(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        now = time.time()

        for trace in store.get_active_traces():
            for span in trace.spans:
                if span.ended_at is not None:
                    continue
                age = now - span.started_at
                if age > self.leak_threshold_s:
                    reports.append(DiagnosticReport(
                        detector="resource_leak",
                        severity=ReportSeverity.WARNING,
                        category=ReportCategory.RESOURCE,
                        trace_id=trace.trace_id,
                        span_id=span.span_id,
                        location=f"span {span.name} ({span.span_id})",
                        message=f"Незавершённый span {span.name} висит {age:.0f}с "
                                f"(порог {self.leak_threshold_s}с)",
                        details={
                            "span_name": span.name,
                            "span_kind": span.kind,
                            "age_s": round(age, 1),
                            "threshold_s": self.leak_threshold_s,
                            "started_at": span.started_at,
                            "trace_name": trace.name,
                        },
                        recommendation="Добавить span.end() в finally-блок или использовать "
                                       "контекстный менеджер",
                    ))

        return reports

    def _check_orphan_spans(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        orphans = store.get_orphan_spans(limit=200)

        connection_orphans = [s for s in orphans if s.kind in CONNECTION_LIKE_KINDS]
        if connection_orphans:
            reports.append(DiagnosticReport(
                detector="resource_leak",
                severity=ReportSeverity.WARNING,
                category=ReportCategory.RESOURCE,
                location="system",
                message=f"{len(connection_orphans)} orphan spans похожи на "
                        f"незакрытые соединения (kind: {', '.join(CONNECTION_LIKE_KINDS)})",
                details={
                    "orphan_count": len(connection_orphans),
                    "connection_kinds": list(CONNECTION_LIKE_KINDS),
                    "total_orphans": len(orphans),
                    "sample": [
                        {"span_id": s.span_id, "name": s.name, "kind": s.kind}
                        for s in connection_orphans[:5]
                    ],
                },
                recommendation="Проверить, что все соединения закрываются. "
                               "Добавить close()/disconnect() в finally.",
            ))

        return reports

    def _check_dangling_traces(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        now = time.time()

        for trace in store.get_active_traces():
            if trace.ended_at is not None:
                continue
            age = now - trace.started_at
            if age > self.leak_threshold_s * 2:
                reports.append(DiagnosticReport(
                    detector="resource_leak",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.RESOURCE,
                    trace_id=trace.trace_id,
                    location=f"trace {trace.name} ({trace.trace_id})",
                    message=f"Активный trace {trace.name} висит {age:.0f}с без завершения",
                    details={
                        "trace_name": trace.name,
                        "age_s": round(age, 1),
                        "span_count": len(trace.spans),
                        "started_at": trace.started_at,
                    },
                    recommendation="Проверить, что trace.end() вызывается во всех сценариях",
                ))

        return reports
