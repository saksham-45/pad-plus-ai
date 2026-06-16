import logging
logger = logging.getLogger(__name__)
"""
ErrorPathDetector — ошибки pipeline без fallback.

Отличает штатную деградацию (DegradationInfo) от реальных ошибок.
"""

from typing import List

from healing.detectors.base import BaseDetector
from healing.report import DiagnosticReport, ReportSeverity, ReportCategory


class ErrorPathDetector(BaseDetector):
    """Ищет error-спаны pipeline без fallback.

    Фильтрует штатную деградацию (DegradationInfo), сообщает только о
    необработанных исключениях и фазах без fallback.
    """

    ERROR_PHASES = {"generate", "rag", "truth_loop", "safety", "episodic"}

    def detect(self) -> List[DiagnosticReport]:
        reports = []
        try:
            from core.xray import get_trace_collector

            tc = get_trace_collector()
            sessions = tc.get_recent_sessions(limit=50)

            for s in sessions:
                meta = s.get("metadata", {})
                stage_times = s.get("stage_times", {})

                has_errors = meta.get("success") is False
                if not has_errors:
                    continue

                # Если это DegradationInfo — штатная ситуация, не ошибка
                degradations = meta.get("degradations", [])
                if degradations:
                    continue

                # Если ответ не пустой — возможно, ошибка обработана
                response = meta.get("response_preview", "")
                if response and "Ошибка" not in response:
                    continue

                reports.append(DiagnosticReport(
                    detector="ErrorPathDetector",
                    severity=ReportSeverity.ERROR,
                    category=ReportCategory.CORRECTNESS,
                    message=f"Pipeline завершился ошибкой без fallback",
                    recommendation="Проверить generate-фазу, включить fallback-провайдер",
                    details={
                        "stages": list(stage_times.keys()),
                        "total_ms": s.get("total_time_ms", 0),
                        "response_preview": response[:100],
                    },
                ))

        except Exception as e:
            logger.warning(f"Operation failed: {e}")
        return reports
