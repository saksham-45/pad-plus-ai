"""
📋 X-Ray History — Хранилище последних трейсов
"""

import logging
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger("padplus.xray")


class XRayHistory:
    """
    Хранит последние 100 трейсов
    """

    def __init__(self, max_traces: int = 100):
        self.max_traces = max_traces
        self.traces = OrderedDict()  # trace_id -> trace
        self.stats = {
            "total_traces": 0,
            "total_errors": 0,
            "avg_latency_ms": 0.0,
            "model_usage": {},
        }

    def add_trace(self, trace) -> None:
        self.traces[trace.id] = trace
        self.stats["total_traces"] += 1

        if not trace.success:
            self.stats["total_errors"] += 1

        # Обновляем среднее время
        n = self.stats["total_traces"]
        self.stats["avg_latency_ms"] = (
            (self.stats["avg_latency_ms"] * (n - 1) + trace.total_ms) / n
        )

        # Считаем использование моделей
        if trace.model:
            self.stats["model_usage"][trace.model] = self.stats["model_usage"].get(trace.model, 0) + 1

        # Удаляем старые
        while len(self.traces) > self.max_traces:
            self.traces.popitem(last=False)

    def get_trace(self, trace_id: str) -> Optional[dict]:
        trace = self.traces.get(trace_id)
        return trace.to_dict() if trace else None

    def get_recent(self, limit: int = 20) -> list:
        traces = list(self.traces.values())[-limit:]
        return [t.to_dict() for t in reversed(traces)]

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "recent_count": len(self.traces),
            "max_traces": self.max_traces,
        }


# Глобальный экземпляр
_history = None


def get_xray_history() -> XRayHistory:
    global _history
    if _history is None:
        _history = XRayHistory()
    return _history
