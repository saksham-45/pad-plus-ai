import logging
logger = logging.getLogger(__name__)
"""
SlowPhasesDetector — фазы pipeline, выполняющиеся дольше порога.
"""

from typing import List

from healing.detectors.base import BaseDetector
from healing.report import DiagnosticReport, ReportSeverity, ReportCategory

# Пороги длительности фаз (ms)
PHASE_THRESHOLDS = {
    "generate": 8000,
    "rag": 2000,
    "truth_loop": 3000,
    "episodic": 2000,
    "knowledge_graph": 2000,
    "emotion": 1000,
    "persona": 1000,
}

# Любая другая фаза
DEFAULT_THRESHOLD_MS = 5000

# Для алерта нужно N медленных из последних M
MIN_SLOW_COUNT = 3
LOOKBACK_WINDOW = 5


class SlowPhasesDetector(BaseDetector):
    """Ищет фазы pipeline, которые стабильно выполняются дольше порога."""

    def __init__(self):
        self._history: dict[str, list[float]] = {}

    def detect(self) -> List[DiagnosticReport]:
        reports = []
        try:
            from core.xray import get_trace_collector

            tc = get_trace_collector()
            sessions = tc.get_recent_sessions(limit=20)

            for s in sessions:
                stage_times = s.get("stage_times", {})
                for phase_name, duration in stage_times.items():
                    threshold = PHASE_THRESHOLDS.get(phase_name, DEFAULT_THRESHOLD_MS)
                    if duration > threshold:
                        h = self._history.setdefault(phase_name, [])
                        h.append(1)
                    else:
                        h = self._history.setdefault(phase_name, [])
                        h.append(0)

            for phase_name, history in self._history.items():
                recent = history[-LOOKBACK_WINDOW:]
                if len(recent) >= MIN_SLOW_COUNT and sum(recent) >= MIN_SLOW_COUNT:
                    threshold = PHASE_THRESHOLDS.get(phase_name, DEFAULT_THRESHOLD_MS)
                    reports.append(DiagnosticReport(
                        detector="SlowPhasesDetector",
                        severity=ReportSeverity.WARNING,
                        category=ReportCategory.PERFORMANCE,
                        message=f"Фаза '{phase_name}' медленная {sum(recent)}/{len(recent)} раз (порог: {threshold}ms)",
                        recommendation=f"Увеличить timeout для {phase_name}, переключить модель или включить кэш",
                        details={
                            "phase": phase_name,
                            "slow_count": sum(recent),
                            "window": len(recent),
                            "threshold_ms": threshold,
                        },
                    ))

            # Ограничим историю
            for k in list(self._history.keys()):
                if len(self._history[k]) > 100:
                    self._history[k] = self._history[k][-100:]

        except Exception as e:
            logger.warning(f"Operation failed: {e}")
        return reports
