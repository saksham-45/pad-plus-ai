from __future__ import annotations

import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.patcher.patterns.base_pattern import BasePattern


RESOURCE_OPEN_CALLS = {"open"}
RESOURCE_OPEN_METHODS = {"open", "connect", "cursor", "acquire"}


class CloseResourcePattern(BasePattern):
    name = "close_resource"
    description = "Оборачивает открытие ресурсов (open, connect) в контекстный менеджер with"
    supported_detectors = ["resource_leak", "resourceleak"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        checker = _ResourceChecker()
        checker.visit(tree)
        return bool(checker.resource_assigns)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        metadata: dict[str, Any] = {"patched_resources": [], "total_patched": 0}

        transformer = _ResourceWithTransformer()
        transformer.visit(tree)

        metadata["patched_resources"] = transformer.patched
        metadata["total_patched"] = len(transformer.patched)
        patched = ast.unparse(tree)
        metadata["diff_lines"] = self._count_diff_lines(source_code, patched)
        return patched, metadata

    @staticmethod
    def _count_diff_lines(original: str, patched: str) -> int:
        import difflib
        diff = difflib.unified_diff(original.splitlines(), patched.splitlines())
        return sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))


class _ResourceChecker(ast.NodeVisitor):
    def __init__(self):
        self.resource_assigns: list[int] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call) and self._is_resource_open(node.value):
            self.resource_assigns.append(node.lineno)
        self.generic_visit(node)

    @staticmethod
    def _is_resource_open(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name) and func.id in RESOURCE_OPEN_CALLS:
            return True
        if isinstance(func, ast.Attribute) and func.attr in RESOURCE_OPEN_METHODS:
            return True
        return False


class _ResourceWithTransformer(ast.NodeTransformer):
    def __init__(self):
        self.patched: list[dict[str, Any]] = []

    def visit_Assign(self, node: ast.Assign) -> ast.Assign | ast.With | None:
        if not isinstance(node.value, ast.Call):
            return node
        call = node.value
        if not self._is_resource_open(call):
            return node
        if len(node.targets) != 1:
            return node
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return node
        var_name = target.id

        with_stmt = ast.With(
            items=[ast.withitem(
                context_expr=call,
                optional_vars=ast.Name(id=var_name, ctx=ast.Store()),
            )],
            body=[
                ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=var_name, ctx=ast.Load()),
                        attr="read", ctx=ast.Load(),
                    ),
                    args=[], keywords=[],
                ))
            ],
        )
        with_stmt.lineno = node.lineno
        with_stmt.end_lineno = node.end_lineno
        with_stmt.col_offset = node.col_offset
        with_stmt.end_col_offset = node.end_col_offset
        with_stmt.type_comment = None

        self.patched.append({
            "variable": var_name,
            "line": node.lineno,
            "resource_call": ast.unparse(call.func) if hasattr(ast, 'unparse') else "",
        })
        return with_stmt

    @staticmethod
    def _is_resource_open(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name) and func.id in RESOURCE_OPEN_CALLS:
            return True
        if isinstance(func, ast.Attribute) and func.attr in RESOURCE_OPEN_METHODS:
            return True
        return False


def apply_close_resource(tree_or_code: ast.Module | str,
                          report: DiagnosticReport | dict | None = None) -> tuple[ast.Module | str, dict[str, Any]]:
    """Backward-compat: accepts (tree, report_dict) or (source_code, report)."""
    pattern = CloseResourcePattern()
    if isinstance(tree_or_code, ast.Module):
        code = ast.unparse(tree_or_code)
        rep = report if isinstance(report, DiagnosticReport) else DiagnosticReport(
            detector="", severity=ReportSeverity.INFO,
            category=ReportCategory.RESOURCE,
            message="", details=report or {},
        )
        patched, meta = pattern.apply(code, rep)
        return ast.parse(patched), meta
    return pattern.apply(tree_or_code, report)
