import logging
logger = logging.getLogger(__name__)
"""
ProviderHealthDetector — мониторинг здоровья провайдеров LLM.
"""

from typing import List

from healing.detectors.base import BaseDetector
from healing.report import DiagnosticReport, ReportSeverity, ReportCategory

FAILURE_RATE_THRESHOLD = 0.3
LOOKBACK_SESSIONS = 50
COOLDOWN_MINUTES = 15


class ProviderHealthDetector(BaseDetector):
    """Следит за стабильностью провайдеров LLM."""

    def __init__(self):
        self._cooldowns: dict[str, float] = {}

    def detect(self) -> List[DiagnosticReport]:
        reports = []
        try:
            from core.xray import get_trace_collector

            tc = get_trace_collector()
            sessions = tc.get_recent_sessions(limit=LOOKBACK_SESSIONS)

            provider_stats: dict[str, dict] = {}
            for s in sessions:
                meta = s.get("metadata", {})
                provider = meta.get("provider")
                if not provider:
                    continue

                stats = provider_stats.setdefault(provider, {"total": 0, "failures": 0})
                stats["total"] += 1
                if meta.get("success") is False:
                    stats["failures"] += 1

            for provider, stats in provider_stats.items():
                if stats["total"] < 3:
                    continue

                failure_rate = stats["failures"] / stats["total"]
                if failure_rate >= FAILURE_RATE_THRESHOLD:
                    reports.append(DiagnosticReport(
                        detector="ProviderHealthDetector",
                        severity=ReportSeverity.WARNING,
                        category=ReportCategory.STABILITY,
                        message=f"Провайдер '{provider}' имеет {failure_rate:.0%} ошибок ({stats['failures']}/{stats['total']})",
                        recommendation=f"Понизить приоритет {provider}, включить fallback через OpenRouter",
                        details={
                            "provider": provider,
                            "failure_rate": round(failure_rate, 3),
                            "failures": stats["failures"],
                            "total": stats["total"],
                        },
                    ))

        except Exception as e:
            logger.warning(f"Operation failed: {e}")
        return reports
