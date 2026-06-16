from __future__ import annotations

import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.patcher.patterns.base_pattern import BasePattern


CLEANUP_FUNCTIONS = {
    "close", "disconnect", "shutdown", "cleanup",
    "release", "free", "destroy", "stop",
}


class TryFinallyPattern(BasePattern):
    name = "try_finally"
    description = "Оборачивает тело функции в try/finally с вызовом cleanup"
    supported_detectors = ["error_path", "errorpath", "span_analyzer", "spananalyzer"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        checker = _TryFinallyGuard()
        checker.visit(tree)
        return bool(checker.candidates)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        metadata: dict[str, Any] = {"patched_functions": [], "total_checks": 0}

        transformer = _TryFinallyTransformer()
        transformer.visit(tree)

        metadata["patched_functions"] = transformer.patched
        metadata["total_checks"] = len(transformer.patched)
        patched = ast.unparse(tree)
        metadata["diff_lines"] = self._count_diff_lines(source_code, patched)
        return patched, metadata

    @staticmethod
    def _count_diff_lines(original: str, patched: str) -> int:
        import difflib
        diff = difflib.unified_diff(original.splitlines(), patched.splitlines())
        return sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))


class _TryFinallyGuard(ast.NodeVisitor):
    """Проверяет, есть ли функции, где нужен try/finally."""

    def __init__(self):
        self.candidates: list[str] = []

    def _has_cleanup_call(self, body: list[ast.stmt]) -> bool:
        finder = _CleanupCallFinder()
        for stmt in body:
            finder.visit(stmt)
        return finder.has_cleanup

    def _has_try_finally(self, body: list[ast.stmt]) -> bool:
        for stmt in body:
            if isinstance(stmt, ast.Try) and stmt.finalbody:
                return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._has_cleanup_call(node.body) and not self._has_try_finally(node.body):
            self.candidates.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)


class _TryFinallyTransformer(ast.NodeTransformer):
    def __init__(self):
        self.patched: list[dict[str, Any]] = []

    def _has_cleanup_call(self, body: list[ast.stmt]) -> bool:
        finder = _CleanupCallFinder()
        for stmt in body:
            finder.visit(stmt)
        return finder.has_cleanup

    def _has_try_finally(self, body: list[ast.stmt]) -> bool:
        for stmt in body:
            if isinstance(stmt, ast.Try) and stmt.finalbody:
                return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef | None:
        self.generic_visit(node)
        if not self._has_cleanup_call(node.body):
            return node
        if self._has_try_finally(node.body):
            return node
        try_stmt = ast.Try(
            body=node.body,
            handlers=[],
            orelse=[],
            finalbody=node.body[-1:],
        )
        node.body = [try_stmt]
        self.patched.append({"function": node.name, "line": node.lineno})
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)


class _CleanupCallFinder(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.has_cleanup = False

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in CLEANUP_FUNCTIONS or node.func.attr == "end":
                self.has_cleanup = True
        self.generic_visit(node)


def apply_try_finally(tree_or_code: ast.Module | str,
                       report: DiagnosticReport | dict | None = None) -> tuple[ast.Module | str, dict[str, Any]]:
    """Backward-compat: accepts (tree, report_dict) or (source_code, report)."""
    pattern = TryFinallyPattern()
    if isinstance(tree_or_code, ast.Module):
        code = ast.unparse(tree_or_code)
        rep = report if isinstance(report, DiagnosticReport) else DiagnosticReport(
            detector="", severity=ReportSeverity.INFO,
            category=ReportCategory.INTEGRITY,
            message="", details=report or {},
        )
        patched, meta = pattern.apply(code, rep)
        return ast.parse(patched), meta
    return pattern.apply(tree_or_code, report)
