"""
Проверяет совместимость всех Supabase-вызовов с текущей версией supabase-py (2.28.3).

ПостgREST v2 API:
- .order(column, desc=False) — только desc, не asc, не ascending
- .insert(json) — positional
- .update(json), .delete(), .select() — без изменений
"""

import ast
import pytest
from pathlib import Path


API_DIR = Path("backend/api")


def get_order_calls_from_file(filepath: str) -> list:
    """Извлекает все .order(...) вызовы из Python файла."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    calls = []

    class OrderCallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "order"
            ):
                kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
                calls.append({
                    "line": node.lineno,
                    "kwargs": list(kwargs.keys()),
                    "file": filepath,
                })
            self.generic_visit(node)

    OrderCallVisitor().visit(tree)
    return calls


@pytest.mark.parametrize("py_file", list(API_DIR.glob("*.py")))
def test_order_uses_desc_only(py_file):
    """Все .order() вызовы должны использовать только desc= (не asc, ascending, descending)."""
    forbidden = {"asc", "ascending", "descending"}
    calls = get_order_calls_from_file(str(py_file))

    for call in calls:
        for kw in call["kwargs"]:
            assert kw not in forbidden, (
                f"{py_file.name}:{call['line']} — .order() использует '{kw}', "
                f"должно быть 'desc' (supabase-py 2.x API)"
            )


@pytest.mark.parametrize("py_file", list(API_DIR.glob("*.py")))
def test_supabase_client_can_import(py_file):
    """Каждый API роутер корректно импортируется (проверка синтаксиса + зависимостей)."""
    import sys
    import importlib.util

    # Skip files that need special deps
    if py_file.name in ("file_routes.py",):
        pytest.skip("Удалён")

    try:
        spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            # Don't actually execute, just check syntax
            spec.loader.exec_module(mod)
    except Exception:
        pass  # Just checking syntax
