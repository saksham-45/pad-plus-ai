"""
🧬 run_diagnostics — запуск всех детекторов с streaming-событиями.
"""

from typing import List, Callable, Optional

from healing.report import DiagnosticReport
from healing.detectors.slow_phases import SlowPhasesDetector
from healing.detectors.error_path import ErrorPathDetector
from healing.detectors.broken_phases import BrokenPhasesDetector
from healing.detectors.provider_health import ProviderHealthDetector
from healing.detectors.strategy_drift import StrategyDriftDetector

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
) -> List[DiagnosticReport]:
    """Запускает все детекторы и возвращает отчёты.

    Args:
        event_callback: вызывается для каждого события (detector_start, detector_found, detector_done)

    Returns:
        Список DiagnosticReport от всех детекторов.
    """
    all_reports: List[DiagnosticReport] = []

    for name, detector in DETECTORS:
        try:
            if event_callback:
                event_callback("detector_start", {"detector": name})

            reports = detector.detect()
            all_reports.extend(reports)

            if reports and event_callback:
                for r in reports:
                    event_callback("detector_found", r.to_dict())

            if event_callback:
                event_callback("detector_done", {"detector": name, "count": len(reports)})

        except Exception as e:
            if event_callback:
                event_callback("detector_error", {"detector": name, "error": str(e)})

    return all_reports


def filter_reports(
    reports: List[DiagnosticReport],
    min_severity: str = "warning",
) -> List[DiagnosticReport]:
    """Фильтрует отчёты по минимальному уровню серьёзности."""
    threshold = MIN_SEVERITY_ORDER.get(min_severity, 1)
    return [r for r in reports if MIN_SEVERITY_ORDER.get(r.severity.value, 0) >= threshold]
