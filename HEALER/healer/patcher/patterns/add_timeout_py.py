from __future__ import annotations

import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.patcher.patterns.base_pattern import BasePattern


HTTP_CALL_NAMES = {
    "get", "post", "put", "delete", "patch", "head", "options", "request",
}

HTTP_MODULES = {"requests", "httpx", "aiohttp", "urllib3", "urllib.request"}

DEFAULT_TIMEOUT = 30.0


class AddTimeoutPattern(BasePattern):
    name = "add_timeout"
    description = "Добавляет timeout параметр к HTTP-вызовам"
    supported_detectors = ["latency_anomaly", "latencyanomaly"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        checker = _TimeoutChecker()
        checker.visit(tree)
        return bool(checker.missing_timeout)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        metadata: dict[str, Any] = {"patched_calls": [], "total_patched": 0}

        transformer = _TimeoutTransformer()
        transformer.visit(tree)

        metadata["patched_calls"] = transformer.patched
        metadata["total_patched"] = len(transformer.patched)
        patched = ast.unparse(tree)
        metadata["diff_lines"] = self._count_diff_lines(source_code, patched)
        return patched, metadata

    @staticmethod
    def _count_diff_lines(original: str, patched: str) -> int:
        import difflib
        diff = difflib.unified_diff(original.splitlines(), patched.splitlines())
        return sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))


class _TimeoutChecker(ast.NodeVisitor):
    def __init__(self):
        self.missing_timeout: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_http_call(node) and not self._has_timeout(node):
            self.missing_timeout.append(node.lineno)
        self.generic_visit(node)

    @staticmethod
    def _is_http_call(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in HTTP_CALL_NAMES:
                return True
        return False

    @staticmethod
    def _has_timeout(node: ast.Call) -> bool:
        return any(kw.arg == "timeout" for kw in node.keywords)


class _TimeoutTransformer(ast.NodeTransformer):
    def __init__(self):
        self.patched: list[dict[str, Any]] = []
        self._current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef | None:
        old = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> ast.Call | None:
        self.generic_visit(node)
        if not self._is_http_call(node):
            return node
        if self._has_timeout(node):
            return node
        node.keywords.append(ast.keyword(arg="timeout", value=ast.Constant(value=DEFAULT_TIMEOUT)))
        self.patched.append({
            "function": self._current_function or "<module>",
            "line": node.lineno,
            "call": ast.unparse(node.func) if hasattr(ast, 'unparse') else "",
        })
        return node

    @staticmethod
    def _is_http_call(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in HTTP_CALL_NAMES:
            return True
        return False

    @staticmethod
    def _has_timeout(node: ast.Call) -> bool:
        return any(kw.arg == "timeout" for kw in node.keywords)


def apply_add_timeout(tree_or_code: ast.Module | str,
                       report: DiagnosticReport | dict | None = None) -> tuple[ast.Module | str, dict[str, Any]]:
    """Backward-compat: accepts (tree, report_dict) or (source_code, report)."""
    pattern = AddTimeoutPattern()
    if isinstance(tree_or_code, ast.Module):
        code = ast.unparse(tree_or_code)
        rep = report if isinstance(report, DiagnosticReport) else DiagnosticReport(
            detector="", severity=ReportSeverity.INFO,
            category=ReportCategory.PERFORMANCE,
            message="", details=report or {},
        )
        patched, meta = pattern.apply(code, rep)
        return ast.parse(patched), meta
    return pattern.apply(tree_or_code, report)
