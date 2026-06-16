from __future__ import annotations

import statistics
from typing import Any

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace
from aethon.xray.span import Span

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector


class SpanAnalyzer(BaseDetector):
    """Анализирует спаны на общие аномалии: дубликаты, missing parents,
    spans без end, необычные depth/kind комбинации."""

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for trace in store.get_completed_traces():
            reports.extend(self._analyze_trace(trace))
        for trace in store.get_active_traces():
            reports.extend(self._analyze_trace(trace))
        return reports

    def _analyze_trace(self, trace: Trace) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        span_map: dict[str, Span] = {s.span_id: s for s in trace.spans}

        span_ids = set()
        for s in trace.spans:
            if s.span_id in span_ids:
                reports.append(DiagnosticReport(
                    detector="span_analyzer",
                    severity=ReportSeverity.ERROR,
                    category=ReportCategory.INTEGRITY,
                    trace_id=trace.trace_id,
                    span_id=s.span_id,
                    location=f"trace {trace.trace_id}",
                    message=f"Обнаружен дубликат span_id: {s.span_id}",
                    details={"span_id": s.span_id, "name": s.name},
                    recommendation="Проверить генерацию span_id на уникальность",
                ))
            span_ids.add(s.span_id)

        for s in trace.spans:
            if s.parent_span_id and s.parent_span_id not in span_map:
                reports.append(DiagnosticReport(
                    detector="span_analyzer",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.INTEGRITY,
                    trace_id=trace.trace_id,
                    span_id=s.span_id,
                    location=f"span {s.name} ({s.span_id})",
                    message=f"Родительский span {s.parent_span_id} не найден в trace",
                    details={
                        "span_id": s.span_id,
                        "name": s.name,
                        "parent_span_id": s.parent_span_id,
                    },
                    recommendation="Проверить parent_span_id: возможно span был создан в другом trace",
                ))

            if s.ended_at is None:
                reports.append(DiagnosticReport(
                    detector="span_analyzer",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.RESOURCE,
                    trace_id=trace.trace_id,
                    span_id=s.span_id,
                    location=f"span {s.name} ({s.span_id})",
                    message=f"Span {s.name} не завершён",
                    details={
                        "span_id": s.span_id,
                        "name": s.name,
                        "started_at": s.started_at,
                        "kind": s.kind,
                    },
                    recommendation="Добавить вызов span.end() во все ветки выполнения",
                ))

        if trace.spans:
            depths = [s.depth for s in trace.spans]
            max_depth = max(depths)
            if max_depth > 10:
                reports.append(DiagnosticReport(
                    detector="span_analyzer",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.MAINTAINABILITY,
                    trace_id=trace.trace_id,
                    location=f"trace {trace.trace_id}",
                    message=f"Глубина trace превышает 10: {max_depth} уровней",
                    details={
                        "max_depth": max_depth,
                        "avg_depth": round(statistics.mean(depths), 1),
                        "span_count": len(trace.spans),
                    },
                    recommendation="Уменьшить вложенность вызовов, упростить pipeline",
                ))

        return reports

    def analyze_trace(self, trace_id: str) -> list[DiagnosticReport]:
        trace = store.get_trace(trace_id)
        if trace is None:
            return [DiagnosticReport(
                detector="span_analyzer",
                severity=ReportSeverity.ERROR,
                category=ReportCategory.INTEGRITY,
                trace_id=trace_id,
                location=f"trace {trace_id}",
                message=f"Trace {trace_id} не найден в хранилище",
                recommendation="Проверить trace_id",
            )]
        return self._analyze_trace(trace)
