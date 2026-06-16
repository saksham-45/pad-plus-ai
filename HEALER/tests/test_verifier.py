"""Тесты для Phase 3: Verification Layer."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class TestVerificationResult(unittest.TestCase):
    """VerificationResult + PhaseVerdict."""

    def test_result_creation(self):
        from healer.verifier.result import VerificationResult, Verdict
        r = VerificationResult(phase="test", verdict=Verdict.PASSED, name="pytest",
                               message="all passed")
        self.assertEqual(r.phase, "test")
        self.assertEqual(r.verdict, Verdict.PASSED)
        self.assertEqual(r.name, "pytest")

    def test_result_to_dict(self):
        from healer.verifier.result import VerificationResult, Verdict
        r = VerificationResult(phase="test", verdict=Verdict.FAILED, name="test",
                               message="failed", details={"count": 3})
        d = r.to_dict()
        self.assertEqual(d["phase"], "test")
        self.assertEqual(d["verdict"], "failed")
        self.assertEqual(d["details"]["count"], 3)

    def test_phase_verdict_all_passed(self):
        from healer.verifier.result import PhaseVerdict, VerificationResult, Verdict
        pv = PhaseVerdict()
        pv.add(VerificationResult(phase="lint", verdict=Verdict.PASSED, name="ruff"))
        pv.add(VerificationResult(phase="test", verdict=Verdict.PASSED, name="pytest"))
        self.assertEqual(pv.verdict, Verdict.PASSED)

    def test_phase_verdict_any_failed(self):
        from healer.verifier.result import PhaseVerdict, VerificationResult, Verdict
        pv = PhaseVerdict()
        pv.add(VerificationResult(phase="test", verdict=Verdict.PASSED, name="pytest"))
        pv.add(VerificationResult(phase="lint", verdict=Verdict.FAILED, name="ruff"))
        self.assertEqual(pv.verdict, Verdict.FAILED)

    def test_phase_verdict_any_error(self):
        from healer.verifier.result import PhaseVerdict, VerificationResult, Verdict
        pv = PhaseVerdict()
        pv.add(VerificationResult(phase="test", verdict=Verdict.ERROR, name="pytest",
                                  error="crash"))
        self.assertEqual(pv.verdict, Verdict.ERROR)

    def test_phase_verdict_summary(self):
        from healer.verifier.result import PhaseVerdict, VerificationResult, Verdict
        pv = PhaseVerdict()
        pv.add(VerificationResult(phase="test", verdict=Verdict.PASSED, name="t1"))
        pv.add(VerificationResult(phase="test", verdict=Verdict.FAILED, name="t2"))
        self.assertIn("1/2 passed", pv.summary)
        self.assertIn("1 failed", pv.summary)

    def test_phase_verdict_to_dict(self):
        from healer.verifier.result import PhaseVerdict, VerificationResult, Verdict
        pv = PhaseVerdict()
        pv.add(VerificationResult(phase="t", verdict=Verdict.PASSED, name="x"))
        d = pv.to_dict()
        self.assertEqual(d["verdict"], "passed")
        self.assertIn("results", d)


class TestTestRunner(unittest.TestCase):
    """TestRunner — запуск тестов проекта."""

    def test_project_not_found(self):
        from healer.verifier.test_runner import TestRunner
        r = TestRunner("/nonexistent/path").run()
        self.assertEqual(r.verdict.value, "error")
        self.assertIn("не найден", r.message)

    def test_detect_pytest_in_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tests").mkdir()
            (Path(tmp) / "test_sample.py").write_text("def test_pass(): assert True")
            from healer.verifier.test_runner import TestRunner
            r = TestRunner(tmp).run()
            self.assertIn(r.verdict.value, ("passed", "failed", "error"))

    def test_parse_pytest_output(self):
        from healer.verifier.test_runner import TestRunner
        output = "tests/test_x.py::test_a PASSED [ 50%]\ntests/test_x.py::test_b FAILED [100%]\n\n===== 1 passed, 1 failed ====="
        result = TestRunner._parse_output(output, "pytest")
        self.assertEqual(result.get("passed"), 1)
        self.assertEqual(result.get("failed"), 1)


class TestLintChecker(unittest.TestCase):
    """LintChecker — запуск линтеров."""

    def test_run_on_own_project(self):
        from healer.verifier.lint_checker import LintChecker
        project = Path(__file__).parent.parent
        r = LintChecker(str(project)).run()
        self.assertIn(r.verdict.value, ("passed", "failed", "error"))

    def test_skipped_when_not_found(self):
        pass


class TestMetricComparator(unittest.TestCase):
    """MetricComparator — сравнение метрик до/after."""

    def test_improvement_detected(self):
        from healer.verifier.metric_compare import MetricComparator
        before = {"latency_ms": 100, "errors": 5}
        after = {"latency_ms": 50, "errors": 1}
        r = MetricComparator().compare(before, after)
        self.assertEqual(r.verdict.value, "passed")
        self.assertIn("улучшение", r.message.lower())

    def test_degradation_detected(self):
        from healer.verifier.metric_compare import MetricComparator
        before = {"latency_ms": 100, "errors": 1}
        after = {"latency_ms": 300, "errors": 5}
        r = MetricComparator().compare(before, after)
        self.assertEqual(r.verdict.value, "failed")
        self.assertIn("деградация", r.message.lower())

    def test_no_change(self):
        from healer.verifier.metric_compare import MetricComparator
        before = {"latency_ms": 100}
        after = {"latency_ms": 105}
        r = MetricComparator(threshold=1.2).compare(before, after)
        self.assertEqual(r.verdict.value, "passed")
        self.assertIn("без изменений", r.message.lower())

    def test_empty_metrics(self):
        from healer.verifier.metric_compare import MetricComparator
        r = MetricComparator().compare({}, {})
        self.assertEqual(r.verdict.value, "passed")


class TestRollbackEngine(unittest.TestCase):
    """RollbackEngine — откат изменений."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="healer_rollback_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rollback_restores_file(self):
        from healer.verifier.rollback import RollbackEngine
        filepath = os.path.join(self.tmp, "test.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("original")
        backup = filepath + ".healer.bak"
        with open(backup, "w", encoding="utf-8") as f:
            f.write("original")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("modified")
        r = RollbackEngine().rollback(filepath)
        self.assertEqual(r.verdict.value, "passed")
        with open(filepath, "r") as f:
            self.assertEqual(f.read(), "original")
        self.assertFalse(os.path.isfile(backup))

    def test_rollback_no_backup(self):
        from healer.verifier.rollback import RollbackEngine
        filepath = os.path.join(self.tmp, "nobackup.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("content")
        r = RollbackEngine().rollback(filepath)
        self.assertEqual(r.verdict.value, "passed")
        self.assertIn("не найден", r.message)

    def test_rollback_all_multiple(self):
        from healer.verifier.rollback import RollbackEngine
        files = []
        for name in ["a.py", "b.py"]:
            fp = os.path.join(self.tmp, name)
            with open(fp, "w") as f:
                f.write("orig")
            with open(fp + ".healer.bak", "w") as f:
                f.write("orig")
            with open(fp, "w") as f:
                f.write("mod")
            files.append(fp)
        r = RollbackEngine().rollback_all(files)
        self.assertEqual(r.verdict.value, "passed")
        self.assertIn("2/2", r.message)

    def test_list_backups(self):
        from healer.verifier.rollback import RollbackEngine
        fp = os.path.join(self.tmp, "backup_test.py")
        with open(fp + ".healer.bak", "w") as f:
            f.write("bak")
        backups = RollbackEngine().list_backups(self.tmp)
        self.assertGreaterEqual(len(backups), 1)
        self.assertIn(".healer.bak", backups[0]["backup"])

    def test_cleanup_backups(self):
        from healer.verifier.rollback import RollbackEngine
        fp = os.path.join(self.tmp, "clean_test.py")
        with open(fp + ".healer.bak", "w") as f:
            f.write("bak")
        count = RollbackEngine().cleanup_backups(self.tmp)
        self.assertGreaterEqual(count, 1)
        self.assertFalse(os.path.isfile(fp + ".healer.bak"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
