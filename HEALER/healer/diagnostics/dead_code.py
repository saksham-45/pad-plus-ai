from __future__ import annotations

from collections import Counter

from aethon.xray.trace_store import store

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector


class DeadCodeDetector(BaseDetector):
    """Находит компоненты (spans по kind), которые зарегистрированы
    в системе, но никогда не вызываются.

    Анализирует все трейсы: если какой-то kind span-ов ни разу не
    встречается, это потенциально мёртвый код."""

    REGISTERED_KINDS = {
        "provider_call",
        "memory_access",
        "gateway_request",
        "telegram_update",
        "skill_execution",
        "core_orchestrate",
        "diagnostic",
        "fallback",
        "import",
        "init",
        "custom",
    }

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        all_traces = store.get_completed_traces() + store.get_active_traces()
        if not all_traces:
            return reports

        used_kinds: Counter[str] = Counter()
        for trace in all_traces:
            for span in trace.spans:
                if span.kind:
                    used_kinds[span.kind] += 1

        for kind in sorted(self.REGISTERED_KINDS):
            if used_kinds[kind] == 0:
                reports.append(DiagnosticReport(
                    detector="dead_code",
                    severity=ReportSeverity.INFO,
                    category=ReportCategory.MAINTAINABILITY,
                    location="system",
                    message=f"Компонент '{kind}' ни разу не вызывался "
                            f"({len(all_traces)} трейсов проанализировано)",
                    details={
                        "kind": kind,
                        "traces_analyzed": len(all_traces),
                        "all_used_kinds": dict(used_kinds.most_common()),
                    },
                    recommendation=f"Проверить, нужен ли компонент '{kind}'. "
                                   f"Если нет — удалить мёртвый код.",
                ))

        unused_trace_names = self._find_unused_trace_names(all_traces)
        for name in unused_trace_names:
            reports.append(DiagnosticReport(
                detector="dead_code",
                severity=ReportSeverity.INFO,
                category=ReportCategory.MAINTAINABILITY,
                location="system",
                message=f"Сценарий '{name}' не использовался ни разу",
                details={
                    "trace_name": name,
                    "traces_analyzed": len(all_traces),
                },
                recommendation="Проверить, нужен ли этот сценарий. Если нет — удалить.",
            ))

        return reports

    def _find_unused_trace_names(self, traces) -> list[str]:
        all_names = Counter(t.name for t in traces)
        registered_scenarios = {
            "user.query", "provider.call", "late.span.test",
            "health.check", "system.init",
        }
        unused = []
        for name in sorted(registered_scenarios):
            if all_names[name] == 0:
                unused.append(name)
        return unused
