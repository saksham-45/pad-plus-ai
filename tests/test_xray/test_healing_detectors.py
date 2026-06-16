"""
Тесты: Self-Healing детекторы.

Проверяют что детекторы корректно находят проблемы
и не дают false positives на здоровых данных.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_trace_collector():
    from core.xray.trace_collector import get_trace_collector
    tc = get_trace_collector()
    tc._sessions.clear()
    tc._active_sessions.clear()
    tc._event_subscribers.clear()
    yield


class TestSlowPhasesDetector:
    """Медленные фазы: generate > 8s, RAG > 2s"""

    def test_detects_slow_generate(self):
        from backend.healing.detectors.slow_phases import SlowPhasesDetector

        detector = SlowPhasesDetector()
        # Симулируем медленные фазы через историю
        for _ in range(5):
            detector._history.setdefault("generate", []).append(1)

        reports = detector.detect()
        slow_reports = [r for r in reports if "generate" in r.message]
        assert len(slow_reports) >= 1

    def test_no_false_positive_on_healthy(self):
        from backend.healing.detectors.slow_phases import SlowPhasesDetector

        detector = SlowPhasesDetector()
        for _ in range(5):
            detector._history.setdefault("generate", []).append(0)

        reports = detector.detect()
        slow_reports = [r for r in reports if "generate" in r.message]
        assert len(slow_reports) == 0


class TestProviderHealthDetector:
    """Провайдер с >30% ошибок"""

    def test_detects_unstable_provider(self):
        from backend.healing.detectors.provider_health import ProviderHealthDetector
        from core.xray.trace_collector import get_trace_collector, TraceSession
        from datetime import datetime

        tc = get_trace_collector()
        for i in range(10):
            rid = f"test_provider_fail_{i}"
            session = TraceSession(
                request_id=rid,
                user_message="test",
                start_time=datetime.now(),
                completed=True,
                metadata={
                    "provider": "gigachat",
                    "success": bool(i < 4),
                    "confidence": 0.5,
                },
            )
            tc._sessions[rid] = session

        detector = ProviderHealthDetector()
        reports = detector.detect()
        gigachat_reports = [r for r in reports if "gigachat" in r.message]
        assert len(gigachat_reports) >= 1

    def test_no_false_positive_on_stable(self):
        from backend.healing.detectors.provider_health import ProviderHealthDetector
        from core.xray.trace_collector import get_trace_collector, TraceSession
        from datetime import datetime

        tc = get_trace_collector()
        for i in range(10):
            rid = f"test_provider_stable_{i}"
            session = TraceSession(
                request_id=rid,
                user_message="test",
                start_time=datetime.now(),
                completed=True,
                metadata={"provider": "openrouter", "success": True, "confidence": 0.9},
            )
            tc._sessions[rid] = session

        detector = ProviderHealthDetector()
        reports = detector.detect()
        assert len(reports) == 0


class TestBrokenPhasesDetector:
    """Пропущенные обязательные фазы"""

    def test_detects_missing_safety(self):
        from backend.healing.detectors.broken_phases import BrokenPhasesDetector
        from core.xray.trace_collector import get_trace_collector, TraceSession
        from datetime import datetime

        tc = get_trace_collector()
        rid = "test_missing_safety"
        session = TraceSession(
            request_id=rid, user_message="test",
            start_time=datetime.now(), completed=True,
        )
        # Добавляем события, чтобы get_summary вернула stage_times
        from core.xray.trace_collector import TraceEvent, TraceStage
        # TraceStage не содержит 'rag', используем RETRIEVE
        stages_map = {"intent": TraceStage.INTENT, "rag": TraceStage.RETRIEVE,
                       "generate": TraceStage.GENERATE}
        for stage, dur in [("intent", 10), ("rag", 20), ("generate", 500)]:
            session.add_event(TraceEvent(
                id=f"e_{stage}", request_id=rid,
                stage=stages_map[stage],
                timestamp=datetime.now(),
                duration_ms=dur,
                data={},
            ))
        tc._sessions[rid] = session

        detector = BrokenPhasesDetector()
        reports = detector.detect()
        safety_reports = [r for r in reports if "safety" in r.message]
        assert len(safety_reports) >= 1

    def test_no_false_positive_on_full(self):
        from backend.healing.detectors.broken_phases import BrokenPhasesDetector
        from core.xray.trace_collector import get_trace_collector, TraceSession, TraceEvent, TraceStage
        from datetime import datetime

        tc = get_trace_collector()
        rid = "test_full_pipeline"
        session = TraceSession(
            request_id=rid, user_message="test",
            start_time=datetime.now(), completed=True,
        )
        stages_map = {"safety": TraceStage.SAFETY, "intent": TraceStage.INTENT,
                       "rag": TraceStage.RETRIEVE, "generate": TraceStage.GENERATE}
        for stage, dur in [("safety", 5), ("intent", 10), ("rag", 20), ("generate", 500)]:
            session.add_event(TraceEvent(
                id=f"e_{stage}", request_id=rid,
                stage=stages_map[stage],
                timestamp=datetime.now(),
                duration_ms=dur,
                data={},
            ))
        tc._sessions[rid] = session

        detector = BrokenPhasesDetector()
        reports = detector.detect()
        assert len(reports) == 0


class TestDiagnosticReport:
    """Формат DiagnosticReport"""

    def test_to_dict(self):
        from backend.healing.report import DiagnosticReport, ReportSeverity, ReportCategory

        report = DiagnosticReport(
            detector="TestDetector",
            severity=ReportSeverity.WARNING,
            category=ReportCategory.PERFORMANCE,
            message="test message",
            recommendation="test recommendation",
        )

        d = report.to_dict()
        assert d["detector"] == "TestDetector"
        assert d["severity"] == "warning"
        assert d["category"] == "performance"
        assert d["message"] == "test message"


class TestRunDiagnostics:
    """Запуск всех детекторов"""

    def test_run_all_detectors(self):
        from backend.healing.runner import run_diagnostics, filter_reports

        events = []

        def on_event(etype, edata):
            events.append((etype, edata))

        reports = run_diagnostics(event_callback=on_event)
        assert isinstance(reports, list)
        # Проверяем что callback вызывался
        assert any("detector_start" in e[0] for e in events)

        filtered = filter_reports(reports, "warning")
        assert isinstance(filtered, list)
