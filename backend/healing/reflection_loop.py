"""
🧠 ReflectionLoop — мета-анализ действий HEALER.
"""

from __future__ import annotations

from typing import Any

from healing.report import DiagnosticReport


def reflect(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    """Анализирует已完成/неудачные циклы и возвращает агрегированные знания.

    Returns:
        {
          "learnings": [...],
          "changes": [...],
          "stats": {...}
        }
    """
    total_cycles = len(cycles)
    success = sum(1 for c in cycles if c.get("status") in {"success", "ok", "done"})
    failed = sum(1 for c in cycles if c.get("status") in {"error", "failed"})
    partial = total_cycles - success - failed
    total_reports = sum(len(c.get("reports", [])) for c in cycles)
    avg_duration = (
        sum(c.get("duration_ms", 0) for c in cycles) / total_cycles if total_cycles else 0
    )

    stats = {
        "total_cycles": total_cycles,
        "success_cycles": success,
        "failed_cycles": failed,
        "partial_cycles": partial,
        "total_reports": total_reports,
        "avg_duration_ms": round(avg_duration, 2),
    }

    learnings: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []

    # Простейшие эвристики на основе истории
    if failed > 0 and total_cycles > 0:
        fail_share = failed / total_cycles
        if fail_share > 0.3:
            learnings.append({
                "title": "Высокий уровень ошибок диагностики",
                "description": f"Доля ошибок: {round(fail_share * 100)}%",
                "impact": "Частые сбои снижают доверие к HEALER",
                "pattern": "repeated_failures",
                "timestamp": "",
            })

    if total_reports > 0:
        learnings.append({
            "title": "Накоплено данных по проблемам",
            "description": f"Всего отчётов: {total_reports}",
            "impact": "Позволяет строить регрессию по severity/модулям",
            "pattern": "data_growth",
            "timestamp": "",
        })

    # Stub changes: пока фиксируем только факт применения
    for c in cycles:
        for r in c.get("reports", []):
            if r.get("status") == "fixed":
                changes.append({
                    "component": r.get("check") or r.get("detector") or r.get("name") or "unknown",
                    "old_value": r.get("old_value"),
                    "new_value": r.get("new_value"),
                    "status": "applied",
                    "reason": "auto-fix по результатам diagnostics",
                    "timestamp": c.get("timestamp", ""),
                })

    return {
        "learnings": learnings,
        "changes": changes,
        "stats": stats,
    }