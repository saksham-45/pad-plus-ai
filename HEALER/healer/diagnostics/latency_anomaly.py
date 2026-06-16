from __future__ import annotations

import statistics
from collections import defaultdict

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector


class LatencyAnomalyDetector(BaseDetector):
    """Находит аномалии задержек: spans, чья длительность значительно
    превышает среднюю по тому же kind/name.

    Собирает статистику по всем трейсам, затем для каждого span
    проверяет, не является ли он выбросом (> 3 sigma от среднего)."""

    STDDEV_MULTIPLIER = 3.0
    MIN_SAMPLES = 3

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        all_traces = store.get_completed_traces() + store.get_active_traces()
        if not all_traces:
            return reports

        stats = self._build_statistics(all_traces)
        for trace in all_traces:
            reports.extend(self._analyze_trace(trace, stats))

        reports.extend(self._check_overall_latency(all_traces))

        return reports

    def _build_statistics(self, traces: list[Trace]) -> dict:
        kind_durations: dict[str, list[float]] = defaultdict(list)
        for trace in traces:
            for span in trace.spans:
                if span.duration_ms is not None:
                    kind_durations[span.kind].append(span.duration_ms)

        stats: dict[str, dict] = {}
        for kind, durations in kind_durations.items():
            if len(durations) < self.MIN_SAMPLES:
                continue
            mean = statistics.mean(durations)
            stdev = statistics.stdev(durations) if len(durations) > 1 else 0
            stats[kind] = {
                "mean": mean,
                "stdev": stdev,
                "count": len(durations),
                "threshold": mean + stdev * self.STDDEV_MULTIPLIER,
            }
        return stats

    def _analyze_trace(self, trace: Trace, stats: dict) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for span in trace.spans:
            if span.duration_ms is None:
                continue
            kind_stat = stats.get(span.kind)
            if kind_stat is None:
                continue
            if span.duration_ms > kind_stat["threshold"]:
                deviation_ratio = span.duration_ms / kind_stat["mean"]
                reports.append(DiagnosticReport(
                    detector="latency_anomaly",
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.PERFORMANCE,
                    trace_id=trace.trace_id,
                    span_id=span.span_id,
                    location=f"span {span.name} ({span.span_id})",
                    message=f"Аномальная задержка {span.name}: {span.duration_ms:.1f}ms "
                            f"(средняя {kind_stat['mean']:.1f}ms, "
                            f"x{deviation_ratio:.1f})",
                    details={
                        "span_name": span.name,
                        "span_kind": span.kind,
                        "duration_ms": span.duration_ms,
                        "mean_ms": round(kind_stat["mean"], 1),
                        "stdev_ms": round(kind_stat["stdev"], 1),
                        "threshold_ms": round(kind_stat["threshold"], 1),
                        "deviation_ratio": round(deviation_ratio, 2),
                        "sample_count": kind_stat["count"],
                        "trace_name": trace.name,
                    },
                    recommendation="Проверить причину задержки: сеть, диск, "
                                   "очередь, блокировка. Добавить timeout или оптимизацию.",
                ))

        return reports

    def _check_overall_latency(self, traces: list[Trace]) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        latencies = [t.duration_ms for t in traces if t.duration_ms is not None]
        if not latencies:
            return reports

        avg = statistics.mean(latencies)
        max_lt = max(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        if max_lt > avg * 5 and len(latencies) > self.MIN_SAMPLES:
            reports.append(DiagnosticReport(
                detector="latency_anomaly",
                severity=ReportSeverity.INFO,
                category=ReportCategory.PERFORMANCE,
                location="system",
                message=f"Максимальная задержка трейса ({max_lt:.0f}ms) в 5+ раз "
                        f"превышает среднюю ({avg:.0f}ms)",
                details={
                    "average_latency_ms": round(avg, 1),
                    "max_latency_ms": round(max_lt, 1),
                    "p95_latency_ms": round(p95, 1),
                    "trace_count": len(latencies),
                },
                recommendation="Проверить выбросы задержек. Возможно, нужен "
                               "circuit breaker или таймауты.",
            ))

        return reports
