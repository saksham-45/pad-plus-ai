from __future__ import annotations

import statistics
from typing import Any

from healer.verifier.result import VerificationResult, Verdict


class MetricComparator:
    """Сравнивает метрики X-RAY до и после исправления.

    Анализирует: количество трейсов, длительность, violations, orphan spans.
    """

    DEGRADATION_THRESHOLD = 1.2

    def __init__(self, threshold: float = DEGRADATION_THRESHOLD):
        self.threshold = threshold

    def compare(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> VerificationResult:
        changes: dict[str, dict[str, Any]] = {}
        degraded: list[str] = []
        improved: list[str] = []

        all_keys = set(before.keys()) | set(after.keys())

        for key in sorted(all_keys):
            b_val = before.get(key)
            a_val = after.get(key)
            if b_val is None or a_val is None:
                continue

            b_num = b_val if isinstance(b_val, (int, float)) else None
            a_num = a_val if isinstance(a_val, (int, float)) else None
            if b_num is None or a_num is None or b_num == 0:
                continue

            ratio = a_num / b_num
            direction = "degraded" if ratio > self.threshold else (
                "improved" if ratio < 1 / self.threshold else "unchanged"
            )

            changes[key] = {
                "before": b_num,
                "after": a_num,
                "ratio": round(ratio, 3),
                "direction": direction,
            }

            if direction == "degraded":
                degraded.append(key)
            elif direction == "improved":
                improved.append(key)

        degraded_count = len(degraded)
        improved_count = len(improved)

        if degraded_count > 0:
            verdict = Verdict.FAILED
            message = f"Деградация {degraded_count} метрик: {', '.join(degraded)}"
        elif improved_count > 0:
            verdict = Verdict.PASSED
            message = f"Улучшение {improved_count} метрик: {', '.join(improved)}"
        else:
            verdict = Verdict.PASSED
            message = "Метрики без изменений"

        return VerificationResult(
            phase="metric",
            verdict=verdict,
            name="metric_comparator",
            message=message,
            details={
                "threshold": self.threshold,
                "degraded_count": degraded_count,
                "improved_count": improved_count,
                "degraded": degraded,
                "improved": improved,
                "changes": changes,
            },
        )

    @staticmethod
    def collect_metrics(store) -> dict[str, Any]:
        """Собирает текущие метрики из trace_store."""
        diag = store.diagnostics() if hasattr(store, 'diagnostics') else {}
        completed = len(store.get_completed_traces()) if hasattr(store, 'get_completed_traces') else 0
        active = len(store.get_active_traces()) if hasattr(store, 'get_active_traces') else 0

        traces = []
        if hasattr(store, 'get_completed_traces'):
            traces = store.get_completed_traces()
        if hasattr(store, 'get_active_traces'):
            traces.extend(store.get_active_traces())

        latencies = [t.duration_ms for t in traces if t.duration_ms is not None]

        return {
            "completed_traces": completed,
            "active_traces": active,
            "orphan_spans": diag.get("orphan_spans", 0) if diag else 0,
            "causal_violations": diag.get("causal_violations", 0) if diag else 0,
            "average_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0,
            "max_latency_ms": round(max(latencies), 1) if latencies else 0,
        }
