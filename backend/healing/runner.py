"""
🧬 run_diagnostics — запуск всех детекторов с streaming-событиями,
сохранением в TraceCollector и ReflectionLoop.
"""

from __future__ import annotations

from typing import Any, List, Callable, Optional

from healing.report import DiagnosticReport
from healing.detectors.slow_phases import SlowPhasesDetector
from healing.detectors.error_path import ErrorPathDetector
from healing.detectors.broken_phases import BrokenPhasesDetector
from healing.detectors.provider_health import ProviderHealthDetector
from healing.detectors.strategy_drift import StrategyDriftDetector

try:
    from core.trace_collector import trace_collector
except Exception:  # pragma: no cover
    trace_collector = None  # type: ignore

try:
    from healing.reflection_loop import reflect
except Exception:  # pragma: no cover
    reflect = None  # type: ignore

DETECTORS = [
    ("SlowPhasesDetector", SlowPhasesDetector()),
    ("ErrorPathDetector", ErrorPathDetector()),
    ("BrokenPhasesDetector", BrokenPhasesDetector()),
    ("ProviderHealthDetector", ProviderHealthDetector()),
    ("StrategyDriftDetector", StrategyDriftDetector()),
]

MIN_SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "error": 2,
    "critical": 3,
}


def run_diagnostics(
    event_callback: Optional[Callable[[str, dict], None]] = None,
    session_id: str = "",
    auto_reflect: bool = True,
) -> List[DiagnosticReport]:
    """Запускает все детекторы и возвращает отчёты.

    Args:
        event_callback: вызывается для каждого события (detector_start, detector_found, detector_done)
        session_id: идентификатор сессии для TraceCollector
        auto_reflect: включить ReflectionLoop после диагностики

    Returns:
        Список DiagnosticReport от всех детекторов.
    """
    all_reports: List[DiagnosticReport] = []
    cycle: dict[str, Any] = {
        "session_id": session_id,
        "reports": [],
        "status": "success",
        "timestamp": "",
    }

    for name, detector in DETECTORS:
        try:
            if event_callback:
                event_callback("detector_start", {"detector": name})

            reports = detector.detect()
            all_reports.extend(reports)
            cycle["reports"].extend([r.to_dict() for r in reports])

            if reports and event_callback:
                for r in reports:
                    event_callback("detector_found", r.to_dict())

            if event_callback:
                event_callback("detector_done", {"detector": name, "count": len(reports)})

        except Exception as e:
            cycle["status"] = "error"
            if event_callback:
                event_callback("detector_error", {"detector": name, "error": str(e)})

    # Сохраняем в TraceCollector
    if session_id and trace_collector:
        try:
            for r in all_reports:
                trace_collector.save_trace(session_id, {
                    "source": "healer",
                    "phase": "diagnostics",
                    "severity": r.severity.value if hasattr(r, "severity") and hasattr(r.severity, "value") else str(getattr(r, "severity", "info")),
                    "timestamp": cycle.get("timestamp", ""),
                    "report": r.to_dict() if hasattr(r, "to_dict") else {},
                })
        except Exception:
            pass

    # ReflectionLoop
    reflection = None
    if auto_reflect and reflect:
        try:
            reflection = reflect([cycle])
        except Exception:
            reflection = None

    if event_callback:
        try:
            event_callback("reflection", reflection or {})
        except Exception:
            pass

    return all_reports


def filter_reports(
    reports: List[DiagnosticReport],
    min_severity: str = "warning",
) -> List[DiagnosticReport]:
    """Фильтрует отчёты по минимальному уровню серьёзности."""
    threshold = MIN_SEVERITY_ORDER.get(min_severity, 1)
    return [r for r in reports if MIN_SEVERITY_ORDER.get(r.severity.value, 0) >= threshold]