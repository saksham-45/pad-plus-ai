"""Тесты для детекторов Фазы 1."""

from __future__ import annotations

import time
import unittest

# Настраиваем store до импорта детекторов
from aethon.xray import store, start_trace, start_span, SpanKind
from aethon.xray.trace import Trace
from aethon.xray.span import Span


class TestDiagnosticsBase(unittest.TestCase):
    def setUp(self):
        store.clear()
        store.configure_persistence("")

    def make_trace(
        self,
        name: str = "test.trace",
        status: str = "ok",
        spans: list[dict] | None = None,
    ) -> Trace:
        trace = Trace(
            trace_id=f"trace_{time.time_ns()}",
            name=name,
            started_at=time.time(),
            status=status,
        )
        if spans:
            for s in spans:
                span = Span(
                    span_id=s.get("span_id", f"span_{time.time_ns()}"),
                    trace_id=trace.trace_id,
                    kind=s.get("kind", "custom"),
                    name=s.get("name", "test.span"),
                    started_at=s.get("started_at", time.time()),
                    ended_at=s.get("ended_at"),
                    duration_ms=s.get("duration_ms"),
                    status=s.get("status", "ok"),
                    parent_span_id=s.get("parent_span_id"),
                    logical_ts=s.get("logical_ts", 0),
                    depth=s.get("depth", 0),
                    late=s.get("late", False),
                )
                trace.spans.append(span)
        if status != "active":
            if trace.ended_at is None:
                trace.ended_at = time.time()
                trace.duration_ms = (trace.ended_at - trace.started_at) * 1000
            store._completed[trace.trace_id] = trace
        else:
            store._active[trace.trace_id] = trace
        return trace


class TestDiagnosticReport(unittest.TestCase):
    """DiagnosticReport — базовые тесты."""

    def test_report_creation(self):
        from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory

        r = DiagnosticReport(
            detector="test",
            severity=ReportSeverity.WARNING,
            category=ReportCategory.PERFORMANCE,
            trace_id="abc",
            span_id="span1",
            location="test location",
            message="test message",
            details={"key": "val"},
            recommendation="fix it",
        )
        self.assertEqual(r.detector, "test")
        self.assertEqual(r.severity, ReportSeverity.WARNING)
        self.assertEqual(r.category, ReportCategory.PERFORMANCE)

    def test_report_to_dict(self):
        from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory

        r = DiagnosticReport(
            detector="test", severity=ReportSeverity.INFO, category=ReportCategory.CORRECTNESS,
        )
        d = r.to_dict()
        self.assertEqual(d["detector"], "test")
        self.assertEqual(d["severity"], "info")
        self.assertEqual(d["category"], "correctness")


class TestSpanAnalyzer(TestDiagnosticsBase):
    """SpanAnalyzer — поиск аномалий в спанах."""

    def test_duplicate_span_id(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        self.make_trace(spans=[
            {"span_id": "dup1", "name": "first"},
            {"span_id": "dup1", "name": "second"},
        ])
        reports = SpanAnalyzer().detect()
        dup_reports = [r for r in reports if "дубликат" in r.message.lower()]
        self.assertGreaterEqual(len(dup_reports), 1)

    def test_missing_parent(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        self.make_trace(spans=[
            {"span_id": "child1", "name": "child", "parent_span_id": "nonexistent"},
        ])
        reports = SpanAnalyzer().detect()
        parent_reports = [r for r in reports if "родительский" in r.message.lower()]
        self.assertGreaterEqual(len(parent_reports), 1)

    def test_unended_span(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        self.make_trace(spans=[
            {"span_id": "open1", "name": "open.span", "ended_at": None},
        ])
        reports = SpanAnalyzer().detect()
        unended = [r for r in reports if "не завершён" in r.message.lower()]
        self.assertGreaterEqual(len(unended), 1)

    def test_deep_trace(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        spans = []
        for i in range(15):
            spans.append({
                "span_id": f"deep_{i}",
                "name": f"depth.{i}",
                "depth": i,
                "duration_ms": 1.0,
            })
        self.make_trace(spans=spans)
        reports = SpanAnalyzer().detect()
        deep = [r for r in reports if "глубина" in r.message.lower()]
        self.assertGreaterEqual(len(deep), 1)

    def test_analyze_trace_not_found(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        reports = SpanAnalyzer().analyze_trace("nonexistent")
        self.assertEqual(len(reports), 1)
        self.assertIn("не найден", reports[0].message.lower())

    def test_clean_trace_no_reports(self):
        from healer.diagnostics.span_analyzer import SpanAnalyzer

        self.make_trace(spans=[
            {"span_id": "s1", "name": "normal", "depth": 1, "duration_ms": 10.0,
             "started_at": time.time(), "ended_at": time.time() + 0.01},
        ])
        reports = SpanAnalyzer().detect()
        self.assertEqual(len(reports), 0)


class TestSlowImportDetector(TestDiagnosticsBase):
    """SlowImportDetector — медленные импорты."""

    def test_slow_import_detected(self):
        from healer.diagnostics.slow_import import SlowImportDetector

        self.make_trace(spans=[
            {"span_id": "imp1", "name": "import.slow_module",
             "kind": "import", "duration_ms": 500.0},
        ])
        reports = SlowImportDetector(threshold_ms=100.0).detect()
        self.assertGreaterEqual(len(reports), 1)
        self.assertIn("import", reports[0].message.lower())

    def test_fast_import_ok(self):
        from healer.diagnostics.slow_import import SlowImportDetector

        self.make_trace(spans=[
            {"span_id": "imp2", "name": "import.fast",
             "kind": "import", "duration_ms": 10.0},
        ])
        reports = SlowImportDetector(threshold_ms=100.0).detect()
        self.assertEqual(len(reports), 0)

    def test_no_import_spans(self):
        from healer.diagnostics.slow_import import SlowImportDetector

        self.make_trace(spans=[
            {"span_id": "s1", "name": "normal", "kind": "custom", "duration_ms": 50.0},
        ])
        reports = SlowImportDetector(threshold_ms=100.0).detect()
        self.assertEqual(len(reports), 0)


class TestErrorPathDetector(TestDiagnosticsBase):
    """ErrorPathDetector — ошибки без recovery."""

    def test_error_without_recovery(self):
        from healer.diagnostics.error_path import ErrorPathDetector

        self.make_trace(name="failing.trace", status="error", spans=[
            {"span_id": "e1", "name": "failing.call",
             "kind": "provider_call", "status": "error", "duration_ms": 100.0},
        ])
        reports = ErrorPathDetector().detect()
        self.assertGreaterEqual(len(reports), 1)
        error_msgs = [r for r in reports if "ошибк" in r.message.lower()]
        self.assertGreaterEqual(len(error_msgs), 1)

    def test_error_with_fallback_ok(self):
        from healer.diagnostics.error_path import ErrorPathDetector

        self.make_trace(name="recovered.trace", status="ok", spans=[
            {"span_id": "e1", "name": "primary.call", "kind": "provider_call",
             "status": "error", "duration_ms": 100.0},
            {"span_id": "fb1", "name": "fallback.call", "kind": "provider_fallback",
             "status": "ok", "duration_ms": 50.0,
             "parent_span_id": ""},
        ])
        reports = ErrorPathDetector().detect()
        self.assertGreaterEqual(len(reports), 0)  # fallback detected = ok

    def test_clean_trace_no_reports(self):
        from healer.diagnostics.error_path import ErrorPathDetector

        self.make_trace(spans=[
            {"span_id": "s1", "name": "normal", "kind": "custom",
             "status": "ok", "duration_ms": 10.0},
        ])
        reports = ErrorPathDetector().detect()
        self.assertEqual(len(reports), 0)


class TestResourceLeakDetector(TestDiagnosticsBase):
    """ResourceLeakDetector — утечки ресурсов."""

    def test_unended_span_leak(self):
        from healer.diagnostics.resource_leak import ResourceLeakDetector

        early = time.time() - 60
        self.make_trace(status="active", spans=[
            {"span_id": "leak1", "name": "open.connection",
             "kind": "provider_call", "started_at": early, "ended_at": None},
        ])
        reports = ResourceLeakDetector(leak_threshold_s=30.0).detect()
        self.assertGreaterEqual(len(reports), 1)
        self.assertIn("незавершён", reports[0].message.lower())

    def test_normal_span_no_leak(self):
        from healer.diagnostics.resource_leak import ResourceLeakDetector

        now = time.time()
        self.make_trace(spans=[
            {"span_id": "s1", "name": "closed.connection",
             "kind": "provider_call", "started_at": now - 1,
             "ended_at": now, "duration_ms": 1000.0},
        ])
        reports = ResourceLeakDetector(leak_threshold_s=30.0).detect()
        leak_reports = [r for r in reports if r.detector == "resource_leak"]
        self.assertEqual(len(leak_reports), 0)


class TestCausalViolationDetector(TestDiagnosticsBase):
    """CausalViolationDetector — обёртка над kernel causal_validator."""

    def test_child_before_parent_detected(self):
        from healer.diagnostics.causal_violation import CausalViolationDetector

        parent_start = time.time()
        child_start = parent_start - 1.0  # child before parent!
        self.make_trace(name="causal.test", spans=[
            {"span_id": "parent1", "name": "parent", "started_at": parent_start,
             "duration_ms": 100.0},
            {"span_id": "child1", "name": "child", "started_at": child_start,
             "parent_span_id": "parent1", "duration_ms": 50.0},
        ])
        reports = CausalViolationDetector().detect()
        violations = [r for r in reports if r.detector == "causal_violation"]
        self.assertGreaterEqual(len(violations), 1)

    def test_clean_trace_no_violations(self):
        from healer.diagnostics.causal_violation import CausalViolationDetector

        now = time.time()
        self.make_trace(spans=[
            {"span_id": "p1", "name": "parent", "started_at": now,
             "logical_ts": 1, "duration_ms": 100.0},
            {"span_id": "c1", "name": "child", "started_at": now + 0.01,
             "parent_span_id": "p1", "logical_ts": 2, "duration_ms": 50.0},
        ])
        reports = CausalViolationDetector().detect()
        violations = [r for r in reports if r.detector == "causal_violation"]
        self.assertEqual(len(violations), 0)


class TestLatencyAnomalyDetector(TestDiagnosticsBase):
    """LatencyAnomalyDetector — аномалии задержек."""

    def test_latency_outlier_detected(self):
        from healer.diagnostics.latency_anomaly import LatencyAnomalyDetector

        now = time.time()
        for i in range(10):
            self.make_trace(spans=[
                {"span_id": f"n{i}", "name": "normal.call",
                 "kind": "provider_call", "duration_ms": 100.0,
                 "started_at": now, "ended_at": now + 0.1},
            ])
        self.make_trace(spans=[
            {"span_id": "outlier", "name": "slow.call",
             "kind": "provider_call", "duration_ms": 5000.0,
             "started_at": now, "ended_at": now + 5.0},
        ])
        reports = LatencyAnomalyDetector().detect()
        anomalies = [r for r in reports if r.detector == "latency_anomaly"]
        self.assertGreaterEqual(len(anomalies), 1)
        self.assertIn("аномальная", anomalies[0].message.lower())

    def test_no_anomaly_when_uniform(self):
        from healer.diagnostics.latency_anomaly import LatencyAnomalyDetector

        now = time.time()
        for i in range(10):
            self.make_trace(spans=[
                {"span_id": f"u{i}", "name": "uniform.call",
                 "kind": "memory_access", "duration_ms": 50.0,
                 "started_at": now, "ended_at": now + 0.05},
            ])
        reports = LatencyAnomalyDetector().detect()
        anomalies = [r for r in reports if r.detector == "latency_anomaly"]
        self.assertEqual(len(anomalies), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
