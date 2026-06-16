import logging
logger = logging.getLogger(__name__)
"""
StrategyDriftDetector — деградация метрик стратегии со временем.
"""

from typing import List

from healing.detectors.base import BaseDetector
from healing.report import DiagnosticReport, ReportSeverity, ReportCategory

MIN_SAMPLES = 5


class StrategyDriftDetector(BaseDetector):
    """Сравнивает execution_time и confidence за последние N запросов
    vs предыдущие N. Если метрики стабильно хуже — алерт."""

    def detect(self) -> List[DiagnosticReport]:
        reports = []
        try:
            from core.xray import get_trace_collector

            tc = get_trace_collector()
            sessions = tc.get_recent_sessions(limit=30)

            strategy_sessions: dict[str, list[dict]] = {}
            for s in sessions:
                meta = s.get("metadata", {})
                strategy = meta.get("strategy", "simple")
                strategy_sessions.setdefault(strategy, []).append({
                    "total_ms": s.get("total_time_ms", 0),
                    "success": meta.get("success", False),
                    "confidence": meta.get("confidence", 0.0),
                })

            for strategy, items in strategy_sessions.items():
                if len(items) < MIN_SAMPLES * 2:
                    continue

                recent = items[:MIN_SAMPLES]
                previous = items[MIN_SAMPLES:MIN_SAMPLES * 2]

                if not recent or not previous:
                    continue

                recent_avg_ms = sum(i["total_ms"] for i in recent) / len(recent)
                prev_avg_ms = sum(i["total_ms"] for i in previous) / len(previous)
                recent_conf = sum(i["confidence"] for i in recent) / len(recent)
                prev_conf = sum(i["confidence"] for i in previous) / len(previous)

                time_drift = recent_avg_ms / max(prev_avg_ms, 1) - 1
                conf_drift = prev_conf - recent_conf

                if time_drift > 0.3 or conf_drift > 0.2:
                    reasons = []
                    if time_drift > 0.3:
                        reasons.append(f"время выросло на {time_drift:.0%}")
                    if conf_drift > 0.2:
                        reasons.append(f"уверенность упала на {conf_drift:.0%}")

                    reports.append(DiagnosticReport(
                        detector="StrategyDriftDetector",
                        severity=ReportSeverity.WARNING,
                        category=ReportCategory.PERFORMANCE,
                        message=f"Стратегия '{strategy}' деградирует: {', '.join(reasons)}",
                        recommendation=f"Рассмотреть смену стратегии или проверку провайдера для {strategy}",
                        details={
                            "strategy": strategy,
                            "time_drift": round(time_drift, 3),
                            "confidence_drift": round(conf_drift, 3),
                            "recent_avg_ms": round(recent_avg_ms, 1),
                            "prev_avg_ms": round(prev_avg_ms, 1),
                        },
                    ))

        except Exception as e:
            logger.warning(f"Operation failed: {e}")
        return reports
