"""
👂 HealerListener — подписка на TraceCollector для само-диагностики.

Тонкая прослойка над PipelineExecutor._mark_degraded():
- Слушает session_completed
- Прогоняет детекторы
- Применяет remediation
- Записывает в MetaLearner
"""

import logging
from typing import Any, Callable, Optional

from healing.runner import run_diagnostics, filter_reports
from healing.remediation import RemediationEngine

logger = logging.getLogger("padplus.healing.listener")


class HealerListener:
    """Подписывается на TraceCollector и запускает healing-цикл."""

    def __init__(self, mode: str = "suggest"):
        self.mode = mode
        self.remediation = RemediationEngine()
        self.remediation.set_mode(mode)
        self._callbacks: list[Callable] = []
        self._cycle_count = 0
        self._last_reports: list[dict] = []

    def on_event(self, callback: Callable):
        self._callbacks.append(callback)

    def _emit(self, event: str, data: dict):
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Operation failed: {e}")
    def _handle_session_completed(self, event_type: str, data: dict):
        if event_type != "session_completed":
            return

        self._cycle_count += 1
        logger.debug(f"🧬 Healer: session completed, running diagnostics (#{self._cycle_count})")

        # Streaming диагностика
        def on_diag_event(etype: str, edata: dict):
            self._emit(f"diag_{etype}", edata)

        all_reports = run_diagnostics(event_callback=on_diag_event)
        self._last_reports = [r.to_dict() for r in all_reports]

        for report in filter_reports(all_reports, "warning"):
            action = self.remediation.process(report)
            if action:
                self.remediation.apply(action, report)

        self._emit("cycle_complete", {
            "cycle": self._cycle_count,
            "reports": len(all_reports),
        })

    def subscribe(self, get_trace_collector_callable: Callable):
        """Подписывается на события TraceCollector."""
        try:
            tc = get_trace_collector_callable()
            tc.subscribe(self._handle_session_completed)
            logger.info("🧬 HealerListener подписан на TraceCollector")
        except Exception as e:
            logger.warning(f"🧬 HealerListener subscribe error: {e}")

    def unsubscribe(self, get_trace_collector_callable: Callable):
        """Отписывается от событий TraceCollector."""
        try:
            tc = get_trace_collector_callable()
            tc.unsubscribe(self._handle_session_completed)
            logger.info("🧬 HealerListener отписан от TraceCollector")
        except Exception as e:
            logger.warning(f"🧬 HealerListener unsubscribe error: {e}")

    def get_last_reports(self, min_severity: str = "info") -> list[dict]:
        threshold = {"info": 0, "warning": 1, "error": 2, "critical": 3}.get(min_severity, 0)
        return [r for r in self._last_reports
                if {"info": 0, "warning": 1, "error": 2, "critical": 3}.get(r.get("severity", "info"), 0) >= threshold]

    def get_status(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "cycle_count": self._cycle_count,
            "remediation_applied": len(self.remediation.get_history()),
            "remediation_history": self.remediation.get_history()[-10:],
            "reports_count": len(self._last_reports),
        }


# Глобальный экземпляр
_healer_listener: Optional[HealerListener] = None


def get_healer() -> HealerListener:
    global _healer_listener
    if _healer_listener is None:
        _healer_listener = HealerListener()
    return _healer_listener
