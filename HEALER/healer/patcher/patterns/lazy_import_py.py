from __future__ import annotations

import ast
import copy
from typing import Any

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.patcher.patterns.base_pattern import BasePattern


class LazyImportPattern(BasePattern):
    name = "lazy_import"
    description = "Переносит импорты с верхнего уровня внутрь функций"
    supported_detectors = ["slow_import", "slowimport"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        finder = _ImportUsageFinder()
        finder.visit(tree)
        return bool(finder.imports_to_move)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        metadata: dict[str, Any] = {"moved_imports": [], "total_functions": 0}

        finder = _ImportUsageFinder()
        finder.visit(tree)

        total_moved = 0
        for func_name, imports_to_move in finder.imports_to_move.items():
            mover = _ImportMover(func_name, imports_to_move, finder.import_usage)
            mover.visit(tree)
            if mover.moved:
                metadata["moved_imports"].append({
                    "function": func_name,
                    "imports": list(imports_to_move),
                })
                total_moved += 1

        metadata["total_moved"] = total_moved
        patched = ast.unparse(tree)
        metadata["diff_lines"] = self._count_diff_lines(source_code, patched)
        return patched, metadata

    @staticmethod
    def _count_diff_lines(original: str, patched: str) -> int:
        import difflib
        diff = difflib.unified_diff(original.splitlines(), patched.splitlines())
        return sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))


class _ImportUsageFinder(ast.NodeVisitor):
    def __init__(self):
        self.function_usages: dict[str, set[str]] = {}
        self.module_level_imports: dict[str, ast.stmt] = {}
        self.current_function: str | None = None
        self.import_usage: dict[str, set[str]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old = self.current_function
        self.current_function = node.name
        self.function_usages.setdefault(node.name, set())
        self.generic_visit(node)
        self.current_function = old

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Import(self, node: ast.Import) -> None:
        if self.current_function is None:
            for alias in node.names:
                name = alias.asname or alias.name
                self.module_level_imports[name] = node
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.current_function is None:
            for alias in node.names:
                name = alias.asname or alias.name
                self.module_level_imports[name] = node
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if self.current_function is not None and isinstance(node.ctx, ast.Load):
            self.function_usages.setdefault(self.current_function, set()).add(node.id)
            self.import_usage.setdefault(node.id, set()).add(self.current_function)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self.current_function is not None and isinstance(node.value, ast.Name) and isinstance(node.ctx, ast.Load):
            self.function_usages.setdefault(self.current_function, set()).add(node.value.id)
            self.import_usage.setdefault(node.value.id, set()).add(self.current_function)
        self.generic_visit(node)

    @property
    def imports_to_move(self) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for imp_name in self.module_level_imports:
            usages = self.import_usage.get(imp_name, set())
            if len(usages) == 1:
                func = next(iter(usages))
                if func not in result:
                    result[func] = set()
                result[func].add(imp_name)
        return result


class _ImportMover(ast.NodeTransformer):
    def __init__(self, func_name: str, imports_to_move: set[str], import_usage: dict[str, set[str]]):
        self.func_name = func_name
        self.imports_to_move = imports_to_move
        self.import_usage = import_usage
        self.moved_imports: list[ast.stmt] = []
        self.moved = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef | None:
        if node.name == self.func_name:
            stmts_to_insert: list[ast.stmt] = []
            for alias_name in self.imports_to_move:
                for stmt in self._find_import(alias_name):
                    stmts_to_insert.append(copy.deepcopy(stmt))
            if stmts_to_insert:
                node.body = list(stmts_to_insert) + list(node.body)
                self.moved = True
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        names_to_keep = []
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in self.imports_to_move:
                names_to_keep.append(alias)
        if not names_to_keep:
            return None
        node.names = names_to_keep
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom | None:
        names_to_keep = []
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in self.imports_to_move:
                names_to_keep.append(alias)
        if not names_to_keep:
            return None
        node.names = names_to_keep
        return node

    def _find_import(self, alias_name: str) -> list[ast.stmt]:
        return []


def apply_lazy_import(tree_or_code: ast.Module | str,
                       report: DiagnosticReport | dict | None = None) -> tuple[ast.Module | str, dict[str, Any]]:
    """Backward-compat: accepts (tree, report_dict) or (source_code, report)."""
    pattern = LazyImportPattern()
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
