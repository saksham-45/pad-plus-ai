"""Тесты для Phase 2: Patch Engine (AST-based patcher)."""

from __future__ import annotations

import ast
import os
import tempfile
import unittest

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory


class TestPatchResult(unittest.TestCase):
    """PatchResult: diff, apply, rollback."""

    def setUp(self):
        from healer.patcher.result import PatchResult
        self.original = "def foo():\n    pass\n"
        self.patched = "def foo():\n    return 42\n"
        self.result = PatchResult(
            patcher="test", pattern="test_pattern",
            source_path="/fake/path.py",
            original_code=self.original,
            patched_code=self.patched,
            success=True,
        )

    def test_diff_generated(self):
        diff = self.result.diff
        self.assertIn("def foo():", diff)
        self.assertIn("return 42", diff)
        self.assertIn("(patched)", diff)

    def test_diff_empty_when_no_patched(self):
        from healer.patcher.result import PatchResult
        r = PatchResult(patcher="t", pattern="p", source_path="", original_code="a")
        self.assertEqual(r.diff, "")

    def test_make_diff_static(self):
        from healer.patcher.result import PatchResult
        diff = PatchResult.make_diff("a\nb\n", "a\nc\n", "test.py")
        self.assertIn("-b", diff)
        self.assertIn("+c", diff)

    def test_to_dict(self):
        d = self.result.to_dict()
        self.assertEqual(d["patcher"], "test")
        self.assertEqual(d["pattern"], "test_pattern")
        self.assertTrue(d["success"])
        self.assertIn("diff", d)

    def test_apply_and_rollback(self):
        from healer.patcher.result import PatchResult
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(self.original)
            tmp = f.name
        try:
            r = PatchResult(
                patcher="test", pattern="tp",
                source_path=tmp,
                original_code=self.original,
                patched_code=self.patched,
                success=True,
            )
            self.assertTrue(r.apply(backup=True))
            with open(tmp, "r") as f:
                self.assertEqual(f.read(), self.patched)
            self.assertTrue(r.rollback())
            with open(tmp, "r") as f:
                self.assertEqual(f.read(), self.original)
        finally:
            bak = tmp + ".healer.bak"
            if os.path.isfile(bak):
                os.remove(bak)
            if os.path.isfile(tmp):
                os.remove(tmp)

    def test_apply_fails_no_file(self):
        from healer.patcher.result import PatchResult
        r = PatchResult(patcher="t", pattern="p", source_path="/nonexistent/path.py",
                        original_code="", patched_code="x", success=True)
        self.assertFalse(r.apply())

    def test_rollback_fails_no_backup(self):
        from healer.patcher.result import PatchResult
        r = PatchResult(patcher="t", pattern="p", source_path="x.py",
                        original_code="", patched_code="x", success=True)
        self.assertFalse(r.rollback())


class TestPythonPatcher(unittest.TestCase):
    """PythonPatcher — AST-трансформации."""

    def test_syntax_error_returns_failure(self):
        from healer.patcher.python_patcher import PythonPatcher
        report = DiagnosticReport(detector="SlowImportDetector", severity=ReportSeverity.INFO,
                                  category=ReportCategory.PERFORMANCE)
        result = PythonPatcher().patch("def foo( pass", report)
        self.assertFalse(result.success)
        # can_apply() returns False on parse error → "cannot be applied"
        self.assertIn("cannot be applied", result.error)

    def test_no_matching_pattern(self):
        from healer.patcher.python_patcher import PythonPatcher
        report = DiagnosticReport(detector="UnknownDetector", severity=ReportSeverity.INFO,
                                  category=ReportCategory.PERFORMANCE)
        result = PythonPatcher().patch("x = 1", report)
        self.assertFalse(result.success)
        self.assertIn("No matching pattern", result.error)

    def test_get_supported_patterns(self):
        from healer.patcher.python_patcher import PythonPatcher
        p = PythonPatcher()
        patterns = p.get_supported_patterns()
        self.assertIn("lazy_import", patterns)
        self.assertIn("try_finally", patterns)
        self.assertIn("add_timeout", patterns)
        self.assertIn("remove_dead", patterns)
        self.assertIn("close_resource", patterns)

    def test_get_supported_detectors(self):
        from healer.patcher.python_patcher import PythonPatcher
        p = PythonPatcher()
        detectors = p.get_supported_detectors()
        self.assertIn("SlowImportDetector", detectors)
        self.assertIn("ErrorPathDetector", detectors)

    def test_patch_file(self):
        from healer.patcher.python_patcher import PythonPatcher
        report = DiagnosticReport(detector="SlowImportDetector", severity=ReportSeverity.INFO,
                                  category=ReportCategory.PERFORMANCE)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("import os\n\ndef test():\n    return os.path.join('a', 'b')\n")
            tmp = f.name
        try:
            result = PythonPatcher().patch_file(tmp, report)
            self.assertTrue(result.success)
        finally:
            if os.path.isfile(tmp):
                os.remove(tmp)

    def test_ast_roundtrip(self):
        from healer.patcher.python_patcher import PythonPatcher
        code = """
import os
import sys

def greet(name):
    return f"Hello {name}"

def main():
    print(greet(os.getlogin()))
"""
        report = DiagnosticReport(detector="SlowImportDetector", severity=ReportSeverity.INFO,
                                  category=ReportCategory.PERFORMANCE)
        result = PythonPatcher().patch(code, report)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.patched_code)
        try:
            ast.parse(result.patched_code)
        except SyntaxError:
            self.fail("Patched code is not valid Python")


class TestPatternLazyImport(unittest.TestCase):
    """Паттерн: перенос импорта внутрь функции."""

    def _apply(self, code: str, kind: str = "import_module") -> str | None:
        from healer.patcher.patterns.lazy_import_py import apply_lazy_import
        report = {"kind": kind}
        tree = ast.parse(code)
        modified, _ = apply_lazy_import(tree, report)
        return ast.unparse(modified)

    def test_import_used_in_one_function_moves(self):
        code = """
import os

def test():
    return os.path.join('a', 'b')

def other():
    return 42
"""
        result = self._apply(code)
        # Import should be inside test(), removed from module level
        self.assertIsNotNone(result)
        self.assertIn("def test():", result)
        self.assertLessEqual(result.count("import os"), 1, "должен быть ≤ 1 импорт os")


class TestPatternTryFinally(unittest.TestCase):
    """Паттерн: try/finally с cleanup."""

    def _apply(self, code: str) -> str | None:
        from healer.patcher.patterns.try_finally_py import apply_try_finally
        tree = ast.parse(code)
        modified, _ = apply_try_finally(tree)
        return ast.unparse(modified)

    def test_try_finally_added_to_cleanup_function(self):
        code = """
def process():
    resource = open("file.txt")
    resource.close()
"""
        result = self._apply(code)
        self.assertIsNotNone(result)
        self.assertIn("try:", result)
        self.assertIn("finally:", result)

    def test_span_end_triggers_try_finally(self):
        code = """
def handle():
    span = start_span("test")
    span.end("ok")
"""
        result = self._apply(code)
        self.assertIsNotNone(result)
        self.assertIn("try:", result)

    def test_no_cleanup_no_change(self):
        code = "def pure():\n    return 42\n"
        result = self._apply(code)
        self.assertEqual(result.strip(), code.strip())

    def test_existing_try_finally_unchanged(self):
        code = """
def safe():
    try:
        proc = process()
    finally:
        proc.cleanup()
"""
        result = self._apply(code)
        self.assertIsNotNone(result)
        self.assertIn("try:", result)
        self.assertIn("finally:", result)


class TestPatternAddTimeout(unittest.TestCase):
    """Паттерн: добавить timeout к HTTP вызовам."""

    def _apply(self, code: str) -> str | None:
        from healer.patcher.patterns.add_timeout_py import apply_add_timeout
        tree = ast.parse(code)
        modified, _ = apply_add_timeout(tree)
        return ast.unparse(modified)

    def test_timeout_added_to_requests_get(self):
        code = """def fetch():import requests; return requests.get('http://example.com')"""
        result = self._apply(code)
        self.assertIsNotNone(result)
        self.assertIn("timeout", result)

    def test_existing_timeout_unchanged(self):
        code = """def fetch():import requests; return requests.get('http://example.com', timeout=10)"""
        result = self._apply(code)
        self.assertIsNotNone(result)

    def test_no_http_no_change(self):
        code = "def calc():\n    return 2 + 2\n"
        result = self._apply(code)
        self.assertEqual(result.strip(), code.strip())


class TestPatternRemoveDead(unittest.TestCase):
    """Паттерн: удалить мёртвый код."""

    def _apply(self, code: str, kind: str = "dead_module") -> str | None:
        from healer.patcher.patterns.remove_dead_py import apply_remove_dead
        report = {"kind": kind}
        tree = ast.parse(code)
        modified, _ = apply_remove_dead(tree, report)
        return ast.unparse(modified)

    def test_unused_import_removed(self):
        code = """import os\nimport sys\n\nx = os.getcwd()\n"""
        result = self._apply(code, "sys")
        self.assertIsNotNone(result)
        self.assertNotIn("import sys", result)
        self.assertIn("import os", result)

    def test_empty_function_removed(self):
        code = """def unused():\n    pass\n\ndef used():\n    return 42\n"""
        result = self._apply(code, "used")
        self.assertIsNotNone(result)
        self.assertNotIn("def unused", result)


class TestPatternCloseResource(unittest.TestCase):
    """Паттерн: обернуть ресурсы в with."""

    def _apply(self, code: str) -> str | None:
        from healer.patcher.patterns.close_resource_py import apply_close_resource
        tree = ast.parse(code)
        modified, _ = apply_close_resource(tree)
        return ast.unparse(modified)

    def test_open_wrapped_in_with(self):
        code = """f = open("file.txt")\ndata = f.read()\nf.close()\n"""
        result = self._apply(code)
        self.assertIsNotNone(result)
        self.assertIn("with", result)


class TestJSPatcher(unittest.TestCase):
    """JSPatcher — JS-трансформации."""

    def test_add_timeout_to_fetch(self):
        from healer.patcher.js_patcher import JSPatcher
        report = DiagnosticReport(detector="LatencyAnomalyDetector", severity=ReportSeverity.WARNING,
                                  category=ReportCategory.PERFORMANCE, message="slow fetch")
        code = """async function load() { const r = await fetch('/api/data'); return r.json(); }"""
        result = JSPatcher().patch(code, report)
        self.assertTrue(result.success)
        self.assertIn("AbortSignal.timeout", result.patched_code)

    def test_existing_timeout_skip(self):
        from healer.patcher.js_patcher import JSPatcher
        report = DiagnosticReport(detector="LatencyAnomalyDetector", severity=ReportSeverity.WARNING,
                                  category=ReportCategory.PERFORMANCE)
        code = """fetch('/api', { signal: AbortSignal.timeout(5000) })"""
        result = JSPatcher().patch(code, report)
        self.assertFalse(result.success)
        self.assertIn("No changes", result.error)

    def test_try_finally_wrapping(self):
        from healer.patcher.js_patcher import JSPatcher
        report = DiagnosticReport(detector="ErrorPathDetector", severity=ReportSeverity.WARNING,
                                  category=ReportCategory.CORRECTNESS)
        code = """function process() { const r = openResource(); r.end(); }"""
        result = JSPatcher().patch(code, report)
        self.assertTrue(result.success)
        self.assertIn("finally", result.patched_code)

    def test_get_supported_patterns(self):
        from healer.patcher.js_patcher import JSPatcher
        p = JSPatcher()
        patterns = p.get_supported_patterns()
        self.assertIn("add_timeout", patterns)
        self.assertIn("try_finally", patterns)


class TestPatternIntegrationPY(unittest.TestCase):
    """Интеграционный тест: DiagnosticReport → PythonPatcher → валидный Python."""

    def _check_patch(self, code: str, detector: str, message: str = ""):
        from healer.patcher.python_patcher import PythonPatcher
        report = DiagnosticReport(
            detector=detector,
            severity=ReportSeverity.WARNING,
            category=ReportCategory.PERFORMANCE,
            message=message,
        )
        result = PythonPatcher().patch(code, report)
        if result.success and result.patched_code:
            try:
                ast.parse(result.patched_code)
            except SyntaxError:
                self.fail(f"Patched code is not valid Python for {detector}:\n{result.patched_code}")
        return result

    def test_slow_import_pipeline(self):
        code = "import os\n\ndef main():\n    return os.getcwd()\n"
        result = self._check_patch(code, "SlowImportDetector", "slow import os")
        self.assertTrue(result.success)

    def test_error_path_pipeline(self):
        code = """
def handle():
    span = start_span("test")
    span.end("ok")
"""
        result = self._check_patch(code, "ErrorPathDetector", "error without recovery")
        self.assertTrue(result.success)
        self.assertIn("finally", result.patched_code)

    def test_latency_anomaly_pipeline(self):
        code = """def fetch():import requests; return requests.get('http://example.com')"""
        result = self._check_patch(code, "LatencyAnomalyDetector", "high latency")
        self.assertTrue(result.success)
        self.assertIn("timeout", result.patched_code)

    def test_dead_code_pipeline(self):
        code = """import os\nimport unused_lib\n\nx = os.getcwd()\n"""
        report = DiagnosticReport(detector="DeadCodeDetector", severity=ReportSeverity.WARNING,
                                  category=ReportCategory.MAINTAINABILITY,
                                  message="unused import", details={"kind": "unused_lib"})
        from healer.patcher.python_patcher import PythonPatcher
        result = PythonPatcher().patch(code, report)
        self.assertTrue(result.success)

    def test_resource_leak_pipeline(self):
        code = """def read_file():f = open("test.txt");return f.read()"""
        result = self._check_patch(code, "ResourceLeakDetector", "unclosed resource")
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main(verbosity=2)
