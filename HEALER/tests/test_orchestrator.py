"""Тесты для Phase 4: Orchestrator."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path


class TestHealerMode(unittest.TestCase):
    """HealerMode enum."""

    def test_mode_values(self):
        from healer.orchestrator import HealerMode
        self.assertEqual(HealerMode.MONITOR.value, "monitor")
        self.assertEqual(HealerMode.SUGGEST.value, "suggest")
        self.assertEqual(HealerMode.AUTO.value, "auto")

    def test_mode_from_string(self):
        from healer.orchestrator import HealerMode
        self.assertEqual(HealerMode("monitor"), HealerMode.MONITOR)
        self.assertEqual(HealerMode("suggest"), HealerMode.SUGGEST)
        self.assertEqual(HealerMode("auto"), HealerMode.AUTO)


class TestHealingCycle(unittest.TestCase):
    """HealingCycle dataclass."""

    def test_defaults(self):
        from healer.orchestrator import HealingCycle, HealerMode
        c = HealingCycle()
        self.assertEqual(c.status, "pending")
        self.assertEqual(c.mode, HealerMode.MONITOR)
        self.assertEqual(c.report_count, 0)

    def test_to_dict(self):
        from healer.orchestrator import HealingCycle, HealerMode
        c = HealingCycle(id="test1", mode=HealerMode.AUTO, started_at=100.0,
                         status="ok", report_count=5)
        d = c.to_dict()
        self.assertEqual(d["id"], "test1")
        self.assertEqual(d["mode"], "auto")
        self.assertEqual(d["report_count"], 5)
        self.assertEqual(d["status"], "ok")


class TestHealerOrchestrator(unittest.TestCase):
    """HealerOrchestrator — основной оркестратор."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="healer_orch_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_defaults(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator()
        self.assertEqual(o.mode.value, "monitor")
        self.assertEqual(len(o.history), 0)
        self.assertIsNone(o.current_cycle)

    def test_init_with_mode(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator(mode="auto")
        self.assertEqual(o.mode.value, "auto")

    def test_set_mode(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator(mode="monitor")
        o.set_mode("auto")
        self.assertEqual(o.mode.value, "auto")
        o.set_mode("suggest")
        self.assertEqual(o.mode.value, "suggest")

    def test_get_mode(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator(mode="suggest")
        self.assertEqual(o.get_mode(), "suggest")

    def test_run_cycle_no_target(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator()
        cycle = o.run_cycle()
        self.assertIn(cycle.status, ("error", "ok"))
        self.assertGreater(len(o.history), 0)

    def test_run_cycle_with_trace_path(self):
        from healer.orchestrator import HealerOrchestrator
        store_path = Path(__file__).parent.parent / "data" / "trace_store"
        if not store_path.exists():
            store_path.mkdir(parents=True, exist_ok=True)
        o = HealerOrchestrator(mode="monitor")
        cycle = o.run_cycle(trace_path=str(store_path))
        self.assertEqual(cycle.status, "ok")
        self.assertGreaterEqual(cycle.report_count, 0)

    def test_run_cycle_monitor_mode(self):
        from healer.orchestrator import HealerOrchestrator
        store_path = Path(__file__).parent.parent / "data" / "trace_store"
        o = HealerOrchestrator(mode="monitor")
        cycle = o.run_cycle(trace_path=str(store_path))
        self.assertEqual(cycle.status, "ok")
        self.assertEqual(len(cycle.patched_files), 0)

    def test_mode_change_in_history(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator(mode="monitor")
        o.set_mode("auto")
        self.assertEqual(o.get_mode(), "auto")

    def test_get_history(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator()
        store_path = Path(__file__).parent.parent / "data" / "trace_store"
        o.run_cycle(trace_path=str(store_path))
        o.run_cycle(trace_path=str(store_path))
        history = o.get_history(limit=5)
        self.assertGreaterEqual(len(history), 2)

    def test_get_status(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator(mode="auto")
        status = o.get_status()
        self.assertEqual(status["mode"], "auto")
        self.assertIn("cycles_total", status)
        self.assertIn("last_cycle", status)

    def test_on_event_callback(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator()
        events: list[str] = []
        def cb(event: str, data: dict):
            events.append(event)
        o.on_event(cb)
        store_path = Path(__file__).parent.parent / "data" / "trace_store"
        o.run_cycle(trace_path=str(store_path))
        self.assertGreaterEqual(len(events), 1)
        self.assertIn(events[0], ("diagnostics", "patch_generated", "patch_applied"))

    def test_patchers_loaded(self):
        from healer.orchestrator import HealerOrchestrator
        o = HealerOrchestrator()
        self.assertIn("SpanAnalyzer", o.patchers)
        self.assertIn("SlowImportDetector", o.patchers)


class TestHealerAPI(unittest.TestCase):
    """API endpoints — базовые тесты."""

    def test_api_routes_defined(self):
        from healer.api import HealerAPIHandler
        self.assertIsNotNone(HealerAPIHandler)


if __name__ == "__main__":
    unittest.main(verbosity=2)
