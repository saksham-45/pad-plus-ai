from __future__ import annotations

import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.patcher.patterns.base_pattern import BasePattern


class RemoveDeadPattern(BasePattern):
    name = "remove_dead"
    description = "Удаляет мёртвый код: неиспользуемые импорты, пустые функции"
    supported_detectors = ["dead_code", "deadcode"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        unused = self._get_unused_names(report)
        checker = _DeadCodeChecker(unused)
        checker.visit(tree)
        return bool(checker.removed_imports)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        metadata: dict[str, Any] = {
            "removed_imports": [],
            "removed_unreachable": 0,
            "removed_empty_functions": 0,
        }

        unused = self._get_unused_names(report)
        cleaner = _DeadCodeCleaner(unused)
        cleaner.visit(tree)

        metadata["removed_imports"] = cleaner.removed_imports
        metadata["removed_unreachable"] = len(cleaner.removed_imports)
        patched = ast.unparse(tree)
        metadata["diff_lines"] = self._count_diff_lines(source_code, patched)
        return patched, metadata

    @staticmethod
    def _get_unused_names(report: DiagnosticReport) -> set[str]:
        unused: set[str] = set()
        kind = report.details.get("kind", "") if report.details else ""
        if kind:
            unused.add(kind)
        return unused

    @staticmethod
    def _count_diff_lines(original: str, patched: str) -> int:
        import difflib
        diff = difflib.unified_diff(original.splitlines(), patched.splitlines())
        return sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))


class _DeadCodeChecker(ast.NodeVisitor):
    def __init__(self, unused_names: set[str]):
        self.unused_names = unused_names
        self.removed_imports: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            if name in self.unused_names:
                self.removed_imports.append({"name": name, "line": node.lineno})
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            if name in self.unused_names:
                self.removed_imports.append({"name": name, "module": node.module, "line": node.lineno})
        self.generic_visit(node)


class _DeadCodeCleaner(ast.NodeTransformer):
    def __init__(self, unused_names: set[str] | None = None):
        self.unused_names = unused_names or set()
        self.removed_imports: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        names_to_keep = []
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in self.unused_names:
                names_to_keep.append(alias)
            else:
                self.removed_imports.append({"name": name, "line": node.lineno})
        if not names_to_keep:
            return None
        node.names = names_to_keep
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom | None:
        names_to_keep = []
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in self.unused_names:
                names_to_keep.append(alias)
            else:
                self.removed_imports.append({"name": name, "module": node.module, "line": node.lineno})
        if not names_to_keep:
            return None
        node.names = names_to_keep
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef | None:
        self.generic_visit(node)
        if self._is_empty(node):
            self.removed_imports.append({
                "function": node.name, "line": node.lineno,
                "action": "removed_empty_function",
            })
            return None
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)

    @staticmethod
    def _is_empty(node: ast.FunctionDef) -> bool:
        body = node.body
        if len(body) == 0:
            return True
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Pass)):
                return True
            if isinstance(stmt, ast.Pass):
                return True
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                val = stmt.value.value
                if isinstance(val, str) and (not val.strip() or val.strip() == '...'):
                    return True
                if isinstance(val, type(Ellipsis)):
                    return True
        return False


def apply_remove_dead(tree_or_code: ast.Module | str,
                       report: DiagnosticReport | dict | None = None) -> tuple[ast.Module | str, dict[str, Any]]:
    """Backward-compat: accepts (tree, report_dict) or (source_code, report)."""
    pattern = RemoveDeadPattern()
    if isinstance(tree_or_code, ast.Module):
        code = ast.unparse(tree_or_code)
        rep = report if isinstance(report, DiagnosticReport) else DiagnosticReport(
            detector="", severity=ReportSeverity.INFO,
            category=ReportCategory.MAINTAINABILITY,
            message="", details=report or {},
        )
        patched, meta = pattern.apply(code, rep)
        return ast.parse(patched), meta
    return pattern.apply(tree_or_code, report)
