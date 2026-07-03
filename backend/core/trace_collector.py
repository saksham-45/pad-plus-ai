"""
🧵 TraceCollector — единая точка сбора трейсов из pipeline и HEALER.
"""

from __future__ import annotations

import threading
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger("padplus.trace_collector")

_SEV_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}


class TraceCollector:
    """In-memory thread-safe collector для трейсов."""

    def __init__(self) -> None:
        self._traces: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[str, dict], None]] = []

    def subscribe(self, callback: Callable[[str, dict], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[str, dict], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _emit(self, event_type: str, data: dict) -> None:
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.warning(f"TraceCollector callback error: {e}")

    def save_trace(self, session_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self._traces[session_id].append(event)
        self._emit("event_recorded", {"session_id": session_id, **event})

    def get_trace(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._traces.get(session_id, []))

    def list_traces(
        self,
        limit: int = 50,
        phase: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает сводку по session_id с опциональной фильтрацией.

        Args:
            limit: макс. количество результатов
            phase: фильтр по фазе (точное совпадение)
            severity: мин. уровень серьёзности (включительно)
        """
        result: list[dict[str, Any]] = []
        min_rank = _SEV_ORDER.get(severity, 0) if severity else 0
        with self._lock:
            for session_id, events in self._traces.items():
                summary = self._summarize(session_id, events)
                if phase and summary.get("phase") != phase:
                    continue
                if severity and _SEV_ORDER.get(summary.get("max_severity", "info"), 0) < min_rank:
                    continue
                result.append(summary)
        result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return result[:limit]

    def _summarize(self, session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        severities = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        phase = ""
        for ev in events:
            sev = ev.get("severity")
            if sev in severities:
                severities[sev] += 1
            if ev.get("phase"):
                phase = ev["phase"]
        max_sev = max(severities, key=lambda k: severities[k]) if any(severities.values()) else "info"
        return {
            "session_id": session_id,
            "events": len(events),
            "phase": phase,
            "severity_counts": severities,
            "max_severity": max_severity_order(severities),
            "updated_at": events[-1].get("timestamp", "") if events else "",
        }


def max_severity_order(counts: dict[str, int]) -> str:
    order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    candidates = [k for k, v in counts.items() if v > 0]
    if not candidates:
        return "info"
    return sorted(candidates, key=lambda k: order.get(k, 0), reverse=True)[0]


# Глобальный инстанс
trace_collector = TraceCollector()