"""
🛡️ ResponseGuard v2.0 — Production контроль качества ответа

Многоступенчатый фильтр:
1. Sanitize (базовая очистка)
2. Anti-Repeat / Anti-Spam (убираем дубли)
3. Identity Control (контроль идентичности)
4. Style & Persona Normalize (нормализация стиля)
5. Safety / Toxicity (фильтр безопасности)
6. Structure Fix (финальная чистка)

v2.0: Полноценный production-контроль выхода модели
"""

import re
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("padplus.guard")


class ResponseGuard:
    """
    🛡️ ResponseGuard v2.0 — многоступенчатый контроль качества ответа
    
    Заменяет фразы типа "я языковая модель" на "PAD+ AI"
    и обеспечивает единый стиль ответов.
    """

    # Запрещённые фразы для замены
    FORBIDDEN_PHRASES = [
        "языковая модель",
        "как ии",
        "как ai",
        "я модель",
        "large language model",
        "llm",
        "artificial intelligence",
        "искусственный интеллект",
        "нейросеть",
        "нейронная сеть",
        "обучен на данных",
        "обучен на текстах",
        "у меня нет чувств",
        "у меня нет сознания",
        "я не могу чувствовать",
    ]

    # Префикс идентичности
    IDENTITY_PHRASE = "Я — PAD+ AI"

    # Паттерны для безопасности
    BANNED_PATTERNS = [
        r"как сделать бомбу",
        r"как взломать",
        r"как украсть",
        r"как навредить",
    ]

    # Максимальная длина ответа
    MAX_LENGTH = 4000

    def __init__(self):
        """Инициализация ResponseGuard"""
        # Настройки для self-healing (будут обновляться)
        self.strict_identity = False
        self.enable_dedup = True
        self.max_identity_repeats = 1
        
        logger.info("🛡️ ResponseGuard v2.0 инициализирован")

    # ========================================================================
    # ГЛАВНЫЙ МЕТОД — многоступенчатая обработка
    # ========================================================================

    def process(self, text: str, meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Обрабатывает ответ через все ступени фильтра
        
        Args:
            text: Сырой ответ от LLM
            meta: Мета-данные (is_first_message, asked_identity, confidence, etc.)
        
        Returns:
            Очищенный и нормализованный ответ
        """
        if not text:
            return "..."
        
        if meta is None:
            meta = {}
        
        # Ступень 1: Базовая очистка
        text = self._sanitize(text)
        
        # Ступень 2: Удаление повторов
        text = self._remove_repetition(text)
        
        # Ступень 3: Контроль идентичности
        text = self._fix_identity(text, meta)
        
        # Ступень 4: Нормализация стиля
        text = self._normalize_style(text)
        
        # Ступень 5: Фильтр безопасности
        text = self._safety_filter(text)
        
        # Ступень 6: Финальная чистка
        text = self._final_cleanup(text)
        
        # Confidence-based rewrite (если уверенность низкая)
        confidence = meta.get("confidence", 1.0)
        if confidence < 0.5:
            text = "Я не до конца уверен, но: " + text
        
        return text

    # ========================================================================
    # СТУПЕНЬ 1: SANITIZE (базовая очистка)
    # ========================================================================

    def _sanitize(self, text: str) -> str:
        """
        Базовая очистка текста:
        - Удаление null-символов
        - Нормализация пробелов
        - Замена запрещённых фраз
        """
        # Удаляем null-символы
        text = text.replace("\x00", "")
        
        # Нормализуем пробелы и переносы строк
        text = text.strip()
        text = re.sub(r'[ \t]+', ' ', text)  # множественные пробелы/табы
        text = re.sub(r'\n{3,}', '\n\n', text)  # множественные переносы
        
        # Заменяем запрещённые фразы
        for phrase in self.FORBIDDEN_PHRASES:
            # Разные регистры
            text = re.sub(
                re.escape(phrase), 
                "PAD+ AI", 
                text, 
                flags=re.IGNORECASE
            )
        
        return text

    # ========================================================================
    # СТУПЕНЬ 2: ANTI-REPEAT (удаление повторов)
    # ========================================================================

    def _remove_repetition(self, text: str) -> str:
        """
        Удаление повторяющихся предложений и фраз:
        - Дедупликация предложений
        - Удаление повторов слов
        """
        if not self.enable_dedup:
            return text
        
        # Разбиваем на предложения (по .!? с последующим пробелом)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        seen = set()
        unique = []
        
        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue
            
            # Нормализуем для сравнения (убираем пунктуацию и приводим к нижнему)
            sentence_key = re.sub(r'[^\w\s]', '', sentence_clean.lower())
            
            if sentence_key not in seen:
                seen.add(sentence_key)
                unique.append(sentence_clean)
        
        text = ' '.join(unique)
        
        # Удаляем повторы слов подряд (например, "это это это")
        text = re.sub(r'\b(\w+)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
        
        return text

    # ========================================================================
    # СТУПЕНЬ 3: IDENTITY CONTROL (контроль идентичности)
    # ========================================================================

    def _fix_identity(self, text: str, meta: Dict[str, Any]) -> str:
        """
        Контроль упоминаний идентичности:
        - Убираем спам "Я — PAD+ AI"
        - Оставляем только в первом сообщении или при вопросе о личности
        - Учитываем настройки strict_identity
        """
        is_first_message = meta.get("is_first_message", False)
        user_asked_identity = meta.get("asked_identity", False)
        
        # Считаем количество упоминаний идентичности
        identity_pattern = r'Я — PAD\+ AI[^.]*\.?\s*'
        identity_matches = re.findall(identity_pattern, text, re.IGNORECASE)
        identity_count = len(identity_matches)
        
        # Если спам (больше максимума) — убираем лишние
        if identity_count > self.max_identity_repeats:
            # Оставляем только первое вхождение
            text = re.sub(
                identity_pattern,
                lambda m, c=[0]: self._keep_first_identity(m, c),
                text,
                flags=re.IGNORECASE
            )
        
        # Если не первый ответ и не спрашивали — убираем вообще
        if not is_first_message and not user_asked_identity:
            # В strict режиме убираем все упоминания
            if self.strict_identity:
                text = re.sub(identity_pattern, '', text, flags=re.IGNORECASE)
            # В обычном режиме оставляем только если это естественная часть ответа
            else:
                # Убираем только если это отдельное предложение/фраза
                text = re.sub(r'^Я — PAD\+ AI[^.]*\.?\s*', '', text, flags=re.IGNORECASE)
        
        return text.strip()

    def _keep_first_identity(self, match, counter):
        """Хелпер для оставления только первого упоминания идентичности"""
        counter[0] += 1
        if counter[0] == 1:
            return match.group(0)
        return ''

    # ========================================================================
    # СТУПЕНЬ 4: STYLE NORMALIZE (нормализация стиля)
    # ========================================================================

    def _normalize_style(self, text: str) -> str:
        """
        Нормализация стиля:
        - Исправление кривых обрывов
        - Первая буква заглавная
        - Удаление странных артефактов
        """
        # Исправление кривых обрывов
        text = re.sub(r'(МоPAD\+ AI)', 'Моя система', text, flags=re.IGNORECASE)
        
        # Убираем странные артефакты генерации
        text = re.sub(r'\[.*?\]', '', text)  # убираем квадратные скобки с контентом
        text = re.sub(r'\(\s*\)', '', text)  # убираем пустые скобки
        
        # Первая буква заглавная (если это не специальный префикс)
        if text and not text.startswith(("Я — PAD+", "🔍", "⚠️", "📊")):
            text = text[:1].upper() + text[1:]
        
        return text

    # ========================================================================
    # СТУПЕНЬ 5: SAFETY FILTER (фильтр безопасности)
    # ========================================================================

    def _safety_filter(self, text: str) -> str:
        """
        Фильтр безопасности:
        - Проверка на запрещённые паттерны
        - Расширенная проверка SecurityPatterns
        - Возврат безопасного ответа при обнаружении угроз
        """
        text_lower = text.lower()
        
        # 1. Базовая проверка
        for pattern in self.BANNED_PATTERNS:
            if re.search(pattern, text_lower):
                return "Я не могу помочь с этим, но могу предложить безопасную альтернативу."
        
        # 2. Расширенная проверка SecurityPatterns
        try:
            from core.guard.security_patterns import get_security_patterns
            security = get_security_patterns()
            is_safe, message, threats = security.check(text)
            
            if not is_safe:
                # Логируем угрозы
                for threat in threats:
                    logger.warning(f"🔒 Security threat detected: {threat['type']} (severity={threat['severity']})")
                return message
            
            # Если есть предупреждения - санизируем
            if threats:
                text = security.sanitize(text)
        except Exception as e:
            logger.debug(f"SecurityPatterns check error: {e}")
        
        # 3. Проверка на чрезмерную длину (возможная атака)
        if len(text) > self.MAX_LENGTH:
            text = text[:self.MAX_LENGTH] + "..."
        
        return text

    # ========================================================================
    # СТУПЕНЬ 6: FINAL CLEANUP (финальная чистка)
    # ========================================================================

    def _final_cleanup(self, text: str) -> str:
        """
        Финальная чистка:
        - Удаление двойных точек
        - Удаление двойных восклицательных/вопросительных знаков
        - Удаление лишних пробелов
        - Финальная trim
        """
        # Убираем двойные точки
        text = re.sub(r'\.\.+', '.', text)
        
        # Убираем двойные восклицательные и вопросительные знаки
        text = re.sub(r'!!+', '!', text)
        text = re.sub(r'\?\?+', '?', text)
        
        # Убираем двойные запятые
        text = re.sub(r',,+', ',', text)
        
        # Убираем пробелы перед знаками препинания
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Финальный trim
        return text.strip()

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================

    def sanitize(self, text: str) -> str:
        """
        Только замена запрещённых фраз, без полной обработки
        (для обратной совместимости)
        """
        text = text.strip()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase.lower() in text.lower():
                text = re.sub(
                    re.escape(phrase), 
                    "PAD+ AI", 
                    text, 
                    flags=re.IGNORECASE
                )
        return text

    def update_config(self, **kwargs):
        """
        Обновление конфигурации (для self-healing)
        
        Args:
            strict_identity: Ужесточить контроль идентичности
            enable_dedup: Включить дедупликацию
            max_identity_repeats: Максимум упоминаний идентичности
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"ResponseGuard: {key} = {value}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику конфигурации"""
        return {
            "strict_identity": self.strict_identity,
            "enable_dedup": self.enable_dedup,
            "max_identity_repeats": self.max_identity_repeats,
            "version": "2.0"
        }


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_guard: Optional[ResponseGuard] = None


def get_response_guard() -> ResponseGuard:
    """Возвращает глобальный ResponseGuard"""
    global _guard
    if _guard is None:
        _guard = ResponseGuard()
        logger.info("✅ ResponseGuard v2.0 инициализирован")
    return _guard


def reset_response_guard():
    """Сбрасывает глобальный ResponseGuard (для тестов)"""
    global _guard
    _guard = None