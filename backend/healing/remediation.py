"""
🔧 RemediationEngine — config-driven исправление проблем.

Не AST, а runtime-изменения: смена модели, включение кэша, fallback провайдера.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import logging

from healing.report import DiagnosticReport, ReportSeverity

logger = logging.getLogger("padplus.healing.remediation")


@dataclass
class RemediationAction:
    """Одно remediate-действие."""
    detector_pattern: str
    condition: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector_pattern": self.detector_pattern,
            "condition": self.condition,
            "action": self.action,
            "params": self.params,
            "description": self.description,
        }


# Таблица remediation: детектор → условие → действие
REMEDIATION_TABLE = [
    RemediationAction(
        detector_pattern="SlowPhasesDetector",
        condition="generate > 8000ms",
        action="switch_model",
        params={"prefer": "groq/llama-3.1-8b", "reason": "generate too slow"},
        description="Переключить на более быструю модель при медленной генерации",
    ),
    RemediationAction(
        detector_pattern="ProviderHealthDetector",
        condition="failure_rate > 0.3",
        action="deprioritize_provider",
        params={"fallback": "openrouter", "reason": "provider unstable"},
        description="Понизить приоритет нестабильного провайдера",
    ),
    RemediationAction(
        detector_pattern="ErrorPathDetector",
        condition="error without fallback",
        action="enable_fallback",
        params={"fallback_provider": "openrouter"},
        description="Включить fallback-провайдер при ошибке генерации",
    ),
    RemediationAction(
        detector_pattern="StrategyDriftDetector",
        condition="time_drift > 0.3",
        action="suggest_strategy_change",
        params={"from_strategy": "reasoning", "to_strategy": "simple"},
        description="Рекомендовать смену стратегии при деградации",
    ),
]


class RemediationEngine:
    """Применяет remediation actions по результатам диагностики."""

    def __init__(self):
        self._applied: list[dict] = []
        self._mode = "suggest"  # monitor / suggest / auto

    def set_mode(self, mode: str):
        self._mode = mode

    def get_mode(self) -> str:
        return self._mode

    def process(self, report: DiagnosticReport) -> Optional[RemediationAction]:
        """Находит подходящее действие для отчёта.

        Returns:
            RemediationAction если найдено, None если нет.
        """
        for action in REMEDIATION_TABLE:
            if action.detector_pattern == report.detector:
                return action
        return None

    def apply(self, action: RemediationAction, report: DiagnosticReport) -> bool:
        """Применяет remediate-действие.

        В режиме monitor — только логирует.
        В режиме suggest — возвращает True (рекомендация).
        В режиме auto — выполняет действие.
        """
        if self._mode == "monitor":
            logger.info(f"🧬 Remediation monitor: {action.description}")
            return False

        if self._mode == "suggest":
            logger.info(f"🧬 Remediation suggest: {action.description}")
            self._applied.append({
                "action": action.to_dict(),
                "status": "suggested",
                "report": report.to_dict(),
            })
            return True

        # auto mode
        try:
            success = self._execute_action(action, report)
            self._applied.append({
                "action": action.to_dict(),
                "status": "applied" if success else "failed",
                "report": report.to_dict(),
            })
            return success
        except Exception as e:
            logger.error(f"🧬 Remediation action failed: {e}")
            self._applied.append({
                "action": action.to_dict(),
                "status": "error",
                "error": str(e),
            })
            return False

    def _execute_action(self, action: RemediationAction, report: DiagnosticReport) -> bool:
        """Исполняет remediate-действие в auto-режиме."""
        if action.action == "switch_model":
            return self._switch_model(action.params, report)
        elif action.action == "deprioritize_provider":
            return self._deprioritize_provider(action.params, report)
        elif action.action == "enable_fallback":
            return self._enable_fallback(action.params, report)
        elif action.action == "suggest_strategy_change":
            return self._suggest_strategy_change(action.params, report)
        return False

    def _switch_model(self, params: dict, report: Optional[DiagnosticReport] = None) -> bool:
        try:
            from runtime.llm_service import get_llm_service
            llm = get_llm_service()
            model = params.get("prefer", "groq/llama-3.1-8b")
            llm.set_default_model(model)
            logger.info(f"🧬 Модель переключена на {model}")
            return True
        except Exception as e:
            logger.warning(f"🧬 switch_model error: {e}")
            return False

    def _deprioritize_provider(self, params: dict, report: Optional[DiagnosticReport] = None) -> bool:
        provider = (report.details.get("provider", "") if report else "") or params.get("provider", "")
        if not provider:
            logger.warning("🧬 deprioritize_provider: провайдер не указан")
            return False
        try:
            from runtime.provider_manager import get_provider_manager
            pm = get_provider_manager()
            pm.disable_provider(provider)
            logger.info(f"🧬 Провайдер {provider} отключён HEALER")
            return True
        except Exception as e:
            logger.warning(f"🧬 deprioritize_provider error: {e}")
            return False

    def _enable_fallback(self, params: dict, report: Optional[DiagnosticReport] = None) -> bool:
        try:
            from runtime.llm_service import get_llm_service
            llm = get_llm_service()
            llm.enable_fallback(params.get("fallback_provider", "openrouter"))
            logger.info(f"🧬 Fallback включён: {params.get('fallback_provider')}")
            return True
        except Exception as e:
            logger.warning(f"🧬 enable_fallback error: {e}")
            return False

    def _suggest_strategy_change(self, params: dict, report: DiagnosticReport) -> bool:
        from_strat = report.details.get("strategy", params.get("from_strategy", "simple"))
        to_strat = params.get("to_strategy", "simple")
        logger.info(
            f"🧬 Смена стратегии: {from_strat} → {to_strat} "
            f"(причина: {report.message})"
        )

        if self._mode == "monitor":
            return False

        try:
            from core.xray.meta_learner import get_meta_learner
            meta = get_meta_learner()
            meta.set_strategy_override(from_strat, to_strat)
            return True
        except Exception as e:
            logger.warning(f"🧬 _suggest_strategy_change error: {e}")
            return False

    def get_history(self) -> list[dict]:
        return list(self._applied)
