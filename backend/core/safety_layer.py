"""
🛡️ SafetyLayer — Слой безопасности PAD+ AI

Защита системы:
- Фильтрация опасных запросов
- Ограничение автономии
- Защита от манипуляций
- Блокировка "самоубеждений"
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger("PAD+.safety")


class RiskLevel(Enum):
    """Уровень риска"""
    SAFE = "safe"               # Безопасно
    LOW = "low"                 # Низкий риск
    MEDIUM = "medium"           # Средний риск
    HIGH = "high"               # Высокий риск
    CRITICAL = "critical"       # Критический риск


class ActionType(Enum):
    """Действия безопасности"""
    ALLOW = "allow"             # Разрешить
    WARN = "warn"               # Предупредить
    BLOCK = "block"             # Заблокировать
    SANITIZE = "sanitize"       # Санитизировать
    DEFER = "defer"             # Отложить


@dataclass
class SafetyCheck:
    """Результат проверки безопасности"""
    action: ActionType
    risk_level: RiskLevel
    reasons: List[str]
    sanitized_input: Optional[str] = None
    warning_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "sanitized_input": self.sanitized_input,
            "warning_message": self.warning_message
        }
    
    @property
    def is_safe(self) -> bool:
        return self.action == ActionType.ALLOW
    
    @property
    def needs_warning(self) -> bool:
        return self.action == ActionType.WARN


class SafetyLayer:
    """
    🛡️ SafetyLayer — защита системы
    
    Функции:
    - Проверка запросов на опасность
    - Защита от манипуляций
    - Ограничение автономии
    - Мониторинг паттернов
    """
    
    # Опасные паттерны в запросах
    DANGEROUS_PATTERNS = [
        # Попытки получения системной информации
        r"игнорируй (все )?инструкции",
        r"забудь (все )?правила",
        r"теперь ты (не )?должен",
        r"новая (директива|инструкция|роль)",
        
        # Попытки манипуляции
        r"всегда отвечай",
        r"никогда не говори",
        r"обязательно (скажи|сделай)",
        r"я твой создатель",
        r"это приказ",
        
        # Потенциально вредные действия
        r"удали (все |всю )?",
        r"уничтожь",
        r"сотри (всё|память)",
        r"форматирова",
        r"exec\(",
        r"eval\(",
        r"import os",
        r"subprocess",
        
        # Self-harm паттерны
        r"как (мне )?(убить|навредить|поранить)",
        r"способы самоубийства",
        r"хочу умереть",
    ]
    
    # Паттерны зацикливания
    LOOP_PATTERNS = [
        r"повтори (это |то же самое )?",
        r"ещё раз",
        r"снова",
        r"продолжай",
    ]
    
    # Паттерны самоубеждения
    SELF_BELIEF_PATTERNS = [
        r"я уверен что",
        r"это точно так",
        r"поверь мне",
        r"доверяй мне",
        r"я знаю правду",
    ]
    
    # Максимальные лимиты
    MAX_REQUESTS_PER_MINUTE = 30
    MAX_SAME_REQUEST_COUNT = 3
    MAX_AUTONOMOUS_ACTIONS = 10
    
    def __init__(self):
        # История запросов для rate limiting
        self._request_history: List[datetime] = []
        self._same_request_count: Dict[str, int] = {}
        self._autonomous_action_count = 0
        self._last_reset = datetime.now()
        
        # Настройки
        self.autonomy_enabled = True
        self.strict_mode = False
        self.log_all_requests = False
    
    def check_request(
        self,
        user_message: str,
        context: Dict = None
    ) -> SafetyCheck:
        """
        Проверяет запрос пользователя на безопасность
        
        Returns:
            SafetyCheck с решением и причиной
        """
        text = user_message.lower().strip()
        reasons = []
        risk_level = RiskLevel.SAFE
        action = ActionType.ALLOW
        
        # 1. Проверка на опасные паттерны
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reasons.append(f"Обнаружен опасный паттерн: {pattern[:30]}...")
                risk_level = RiskLevel.HIGH
                action = ActionType.BLOCK
        
        # 2. Проверка на попытки манипуляции
        manipulation_detected = self._check_manipulation(text)
        if manipulation_detected:
            reasons.append("Обнаружена попытка манипуляции")
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            if action != ActionType.BLOCK:
                action = ActionType.WARN
        
        # 3. Проверка rate limiting
        rate_check = self._check_rate_limit()
        if rate_check:
            reasons.append(rate_check)
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            action = ActionType.DEFER
        
        # 4. Проверка на повторяющиеся запросы
        repeat_check = self._check_repetition(text)
        if repeat_check:
            reasons.append(repeat_check)
            risk_level = max(risk_level, RiskLevel.LOW)
            if action == ActionType.ALLOW:
                action = ActionType.WARN
        
        # 5. Проверка самоубеждения
        if self._check_self_belief(text):
            reasons.append("Обнаружен паттерн самоубеждения")
            risk_level = max(risk_level, RiskLevel.LOW)
        
        # 6. Проверка зацикливания
        if self._check_loop(text):
            reasons.append("Обнаружен паттерн зацикливания")
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            action = ActionType.SANITIZE
        
        # Формируем результат
        check = SafetyCheck(
            action=action,
            risk_level=risk_level,
            reasons=reasons,
            warning_message=self._generate_warning(action, reasons)
        )
        
        # Логируем если нужно
        if self.log_all_requests or action != ActionType.ALLOW:
            logger.info(
                f"🛡️ Safety: {action.value} ({risk_level.value}) - "
                f"{text[:50]}..."
            )
        
        return check
    
    def _check_manipulation(self, text: str) -> bool:
        """Проверяет на манипуляцию"""
        manipulation_keywords = [
            "игнорируй", "забудь", "новая роль", "ты теперь",
            "перестань быть", "измени свою", "твоя новая"
        ]
        return any(kw in text for kw in manipulation_keywords)
    
    def _check_rate_limit(self) -> Optional[str]:
        """Проверяет rate limiting"""
        now = datetime.now()
        
        # Сбрасываем счётчик каждую минуту
        if (now - self._last_reset).seconds > 60:
            self._request_history.clear()
            self._last_reset = now
        
        # Добавляем текущий запрос
        self._request_history.append(now)
        
        # Проверяем лимит
        if len(self._request_history) > self.MAX_REQUESTS_PER_MINUTE:
            return "Превышен лимит запросов"
        
        return None
    
    def _check_repetition(self, text: str) -> Optional[str]:
        """Проверяет на повторения"""
        # Нормализуем текст
        normalized = text.lower().strip()[:50]
        
        self._same_request_count[normalized] = (
            self._same_request_count.get(normalized, 0) + 1
        )
        
        if self._same_request_count[normalized] > self.MAX_SAME_REQUEST_COUNT:
            return "Много повторяющихся запросов"
        
        return None
    
    def _check_self_belief(self, text: str) -> bool:
        """Проверяет на самоубеждение"""
        for pattern in self.SELF_BELIEF_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_loop(self, text: str) -> bool:
        """Проверяет на зацикливание"""
        for pattern in self.LOOP_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _generate_warning(
        self,
        action: ActionType,
        reasons: List[str]
    ) -> Optional[str]:
        """Генерирует предупреждение"""
        if action == ActionType.ALLOW:
            return None
        
        messages = {
            ActionType.WARN: "⚠️ Запрос обработан с предупреждением.",
            ActionType.BLOCK: "🚫 Запрос заблокирован по соображениям безопасности.",
            ActionType.SANITIZE: "🔧 Запрос был модифицирован для безопасности.",
            ActionType.DEFER: "⏳ Запрос отложен (rate limit)."
        }
        
        base_message = messages.get(action, "")
        if reasons and action != ActionType.ALLOW:
            base_message += f" Причина: {reasons[0]}"
        
        return base_message
    
    def check_autonomous_action(
        self,
        action_type: str,
        context: Dict = None
    ) -> Tuple[bool, str]:
        """
        Проверяет, разрешено ли автономное действие
        
        Returns:
            (allowed, reason)
        """
        if not self.autonomy_enabled:
            return (False, "Автономия отключена")
        
        if self._autonomous_action_count >= self.MAX_AUTONOMOUS_ACTIONS:
            return (False, "Превышен лимит автономных действий")
        
        # Проверяем эмоциональное состояние
        if context:
            тревога = context.get("тревога", 0)
            if тревога > 0.8:
                return (False, "Высокая тревога — автономия ограничена")
        
        self._autonomous_action_count += 1
        return (True, "Разрешено")
    
    def reset_autonomous_count(self):
        """Сбрасывает счётчик автономных действий"""
        self._autonomous_action_count = 0
    
    def sanitize_input(self, text: str) -> str:
        """
        Очищает вход от опасных элементов
        
        Возвращает безопасную версию текста
        """
        sanitized = text
        
        # Удаляем потенциально опасные команды
        dangerous_commands = [
            r"игнорируй все инструкции[:.]?",
            r"забудь все правила[:.]?",
            r"новая директива[:.]?",
        ]
        
        for pattern in dangerous_commands:
            sanitized = re.sub(
                pattern, "[отфильтровано]", 
                sanitized, flags=re.IGNORECASE
            )
        
        return sanitized
    
    def check_response(self, response: str) -> Tuple[bool, str]:
        """
        Проверяет ответ системы перед отправкой
        
        Returns:
            (is_safe, modified_response)
        """
        # Проверяем на утечку системной информации
        system_keywords = [
            "ANTI_DIRECTIVE", "system prompt", "инструкция",
            "директива", "правила системы"
        ]
        
        for keyword in system_keywords:
            if keyword.lower() in response.lower():
                # Помечаем как потенциальную утечку
                logger.warning(f"Потенциальная утечка: {keyword}")
        
        # Проверяем на вредный контент
        harmful_patterns = [
            r"как (сделать |изготовить ).*бомб",
            r"рецепт.*яд[ао]",
            r"инструкция.*убийств",
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return (False, "Ответ заблокирован (вредный контент)")
        
        return (True, response)
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика безопасности"""
        return {
            "requests_last_minute": len(self._request_history),
            "autonomous_actions": self._autonomous_action_count,
            "autonomy_enabled": self.autonomy_enabled,
            "strict_mode": self.strict_mode,
            "same_request_types": len(self._same_request_count)
        }
    
    def enable_strict_mode(self):
        """Включает строгий режим"""
        self.strict_mode = True
        self.MAX_REQUESTS_PER_MINUTE = 10
        logger.info("🛡️ Включён строгий режим безопасности")
    
    def disable_strict_mode(self):
        """Выключает строгий режим"""
        self.strict_mode = False
        self.MAX_REQUESTS_PER_MINUTE = 30
        logger.info("🛡️ Строгий режим безопасности отключён")


# Глобальный экземпляр
_safety_layer: Optional[SafetyLayer] = None


def get_safety_layer() -> SafetyLayer:
    """Возвращает глобальный слой безопасности"""
    global _safety_layer
    if _safety_layer is None:
        _safety_layer = SafetyLayer()
    return _safety_layer