import logging
logger = logging.getLogger(__name__)
"""
BrokenPhasesDetector — обязательные фазы pipeline не выполнились.
"""

from typing import List

from healing.detectors.base import BaseDetector
from healing.report import DiagnosticReport, ReportSeverity, ReportCategory

REQUIRED_PHASES = {"safety", "intent", "generate"}
CRITICAL_PHASES = {"safety"}


class BrokenPhasesDetector(BaseDetector):
    """Проверяет что все обязательные фазы выполнились."""

    def detect(self) -> List[DiagnosticReport]:
        reports = []
        try:
            from core.xray import get_trace_collector

            tc = get_trace_collector()
            sessions = tc.get_recent_sessions(limit=50)

            for s in sessions:
                stage_times = s.get("stage_times", {})
                executed = set(stage_times.keys())

                missing = REQUIRED_PHASES - executed
                if not missing:
                    continue

                for phase in missing:
                    severity = ReportSeverity.CRITICAL if phase in CRITICAL_PHASES else ReportSeverity.ERROR
                    reports.append(DiagnosticReport(
                        detector="BrokenPhasesDetector",
                        severity=severity,
                        category=ReportCategory.INTEGRITY,
                        message=f"Обязательная фаза '{phase}' не выполнилась",
                        recommendation=f"Перезапустить pipeline state, проверить executor.phase_map",
                        details={
                            "missing_phase": phase,
                            "executed_phases": sorted(executed),
                        },
                    ))

        except Exception as e:
            logger.warning(f"Operation failed: {e}")
        return reports
