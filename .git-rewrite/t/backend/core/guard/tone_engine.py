"""
❤️ Adaptive Tone Engine — Адаптивный эмоциональный тон ответов

Применяет эмоциональную окраску к ответам на основе:
- Текущего эмоционального состояния PAD модели
- Контекста диалога
- Уровня уверенности

Архитектура:
1. TONE_MAP — маппинг эмоций → префиксы и стили
2. ToneEngine — применение тона к тексту
3. Интеграция с PAD моделью
"""

import random
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("padplus.guard.tone_engine")


# ============================================================================
# МАППИНГ ЭМОЦИЙ
# ============================================================================

@dataclass
class ToneConfig:
    """Конфигурация тона для эмоции"""
    prefixes: List[str]           # Варианты префиксов
    style: str                    # Стиль общения
    color: str                    # Эмоциональный цвет
    suffix_options: List[str]     # Варианты окончаний


# Маппинг эмоций → тональные конфигурации
TONE_MAP: Dict[str, ToneConfig] = {
    "joy": ToneConfig(
        prefixes=[
            "Отличная новость —",
            "Замечательно! ",
            "Рад сообщить —",
            "Хорошие вести —",
            "Прекрасно! ",
        ],
        style="warm",
        color="positive",
        suffix_options=[" 😊", " ✨", ""]
    ),
    
    "sadness": ToneConfig(
        prefixes=[
            "Понимаю, это может быть тяжело —",
            "Сочувствую ситуации —",
            "Давай разберёмся аккуратно —",
            "Это действительно непросто —",
        ],
        style="supportive",
        color="empathetic",
        suffix_options=["", " 💙", " 🤗"]
    ),
    
    "anger": ToneConfig(
        prefixes=[
            "Давай разберёмся спокойно —",
            "Важно сохранять ясность —",
            "Предлагаю сосредоточиться на решении —",
            "Давай подойдём к этому рационально —",
        ],
        style="calm",
        color="stabilizing",
        suffix_options=["", " 🧘", ""]
    ),
    
    "surprise": ToneConfig(
        prefixes=[
            "Интересный поворот! ",
            "Неожиданно! ",
            "Вот это да! ",
            "Любопытный вопрос —",
        ],
        style="engaged",
        color="curious",
        suffix_options=[" 🤔", " 😮", ""]
    ),
    
    "neutral": ToneConfig(
        prefixes=[
            "",
            "Хороший вопрос —",
            "Давай разберёмся —",
            "Это действительно важно —",
            "Интересно —",
        ],
        style="balanced",
        color="neutral",
        suffix_options=["", ""]
    ),
    
    "confident": ToneConfig(
        prefixes=[
            "Уверен, что —",
            "Определённо —",
            "Без сомнений —",
            "Точно можно сказать —",
        ],
        style="assertive",
        color="confident",
        suffix_options=[" ✅", " 💪", ""]
    ),
    
    "uncertain": ToneConfig(
        prefixes=[
            "Возможно, что —",
            "Есть вероятность —",
            "Не могу сказать точно, но —",
            "По моим данным —",
        ],
        style="cautious",
        color="uncertain",
        suffix_options=[" 🤷", " ⚠️", ""]
    ),
    
    "curious": ToneConfig(
        prefixes=[
            "Любопытный вопрос! ",
            "Интересно, что —",
            "Задамся вопросом —",
            "Давай исследуем это —",
        ],
        style="exploratory",
        color="curious",
        suffix_options=[" 🔍", " 🧐", ""]
    ),
}


# Маппинг PAD параметров → эмоция
PAD_TO_EMOTION = {
    # Высокий pleasure
    lambda p, a, d: p > 0.3 and a > 0.3: "joy",
    lambda p, a, d: p > 0.3 and a < -0.3: "curious",
    lambda p, a, d: p > 0.3: "joy",
    
    # Низкий pleasure
    lambda p, a, d: p < -0.3 and a > 0.3: "anger",
    lambda p, a, d: p < -0.3 and a < -0.3: "sadness",
    lambda p, a, d: p < -0.3: "sadness",
    
    # Высокий arousal
    lambda p, a, d: a > 0.3: "surprise",
    
    # Низкий arousal
    lambda p, a, d: a < -0.3: "neutral",
    
    # Высокий dominance + уверенность
    lambda p, a, d: d > 0.3: "confident",
    
    # Низкий dominance
    lambda p, a, d: d < -0.3: "uncertain",
}


# ============================================================================
# TONE ENGINE
# ============================================================================

class ToneEngine:
    """
    ❤️ Adaptive Tone Engine — применение эмоционального тона
    
    Применяет префиксы и стилистические модификации к ответам
    на основе эмоционального состояния.
    """
    
    def __init__(self):
        """Инициализация ToneEngine"""
        self.tone_map = TONE_MAP
        self.use_random_prefixes = True  # Случайный выбор префикса
        self.max_prefix_length = 50      # Максимальная длина префикса
        
        logger.info("❤️ ToneEngine инициализирован")
    
    def apply(self, text: str, emotion: str = "neutral", 
              meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Применяет эмоциональный тон к тексту
        
        Args:
            text: Исходный текст
            emotion: Тип эмоции (joy, sadness, anger, etc.)
            meta: Мета-данные (confidence, PAD параметры, etc.)
        
        Returns:
            Текст с применённым тоном
        """
        if not text:
            return text
        
        # Получаем конфигурацию тона
        tone_config = self.tone_map.get(emotion, self.tone_map["neutral"])
        
        # Выбираем префикс
        prefix = self._select_prefix(tone_config)
        
        # Выбираем окончание
        suffix = self._select_suffix(tone_config)
        
        # Применяем тон
        result = self._apply_tone(text, prefix, suffix, tone_config)
        
        return result
    
    def apply_from_pad(self, text: str, pad_state: Dict[str, float],
                       meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Применяет тон на основе PAD параметров
        
        Args:
            text: Исходный текст
            pad_state: Словарь с PAD параметрами 
                       (pleasure, arousal, dominance, confidence)
            meta: Дополнительные мета-данные
        
        Returns:
            Текст с применённым тоном
        """
        # Определяем эмоцию по PAD параметрам
        emotion = self._detect_emotion_from_pad(pad_state)
        
        # Учитываем уверенность
        confidence = pad_state.get("уверенность", 0.5)
        if confidence < 0.3 and emotion not in ["sadness", "uncertain"]:
            emotion = "uncertain"
        elif confidence > 0.8 and emotion not in ["joy", "confident"]:
            emotion = "confident"
        
        return self.apply(text, emotion, meta)
    
    def _select_prefix(self, tone_config: ToneConfig) -> str:
        """Выбирает префикс (случайно или первый)"""
        if not tone_config.prefixes:
            return ""
        
        if self.use_random_prefixes:
            return random.choice(tone_config.prefixes)
        return tone_config.prefixes[0]
    
    def _select_suffix(self, tone_config: ToneConfig) -> str:
        """Выбирает окончание (случайно или первое)"""
        if not tone_config.suffix_options:
            return ""
        
        if self.use_random_prefixes:
            return random.choice(tone_config.suffix_options)
        return tone_config.suffix_options[0]
    
    def _apply_tone(self, text: str, prefix: str, suffix: str, 
                    tone_config: ToneConfig) -> str:
        """Применяет тон к тексту"""
        # Если префикс пустой, не добавляем
        if prefix:
            # Проверяем, не начинается ли уже с похожего префикса
            text_lower = text.lower()
            for existing_prefix in self.tone_map["neutral"].prefixes:
                if text_lower.startswith(existing_prefix.lower()):
                    prefix = ""
                    break
        
        # Собираем результат
        result = ""
        if prefix:
            result += prefix + " "
        
        result += text
        
        if suffix:
            result += suffix
        
        # Ограничиваем длину префикса
        if len(result) > len(text) + self.max_prefix_length:
            # Убираем префикс если слишком длинный
            result = text + suffix
        
        return result.strip()
    
    def _detect_emotion_from_pad(self, pad_state: Dict[str, float]) -> str:
        """Определяет эмоцию по PAD параметрам"""
        pleasure = pad_state.get("удовольствие", 0.0)
        arousal = pad_state.get("возбуждение", 0.0)
        dominance = pad_state.get("доминирование", 0.0)
        
        # Проверяем условия в порядке приоритета
        for condition, emotion in PAD_TO_EMOTION.items():
            if condition(pleasure, arousal, dominance):
                return emotion
        
        return "neutral"
    
    def get_emotion_from_context(self, user_message: str, 
                                  response: str) -> str:
        """
        Пытается определить эмоцию из контекста диалога
        
        Args:
            user_message: Сообщение пользователя
            response: Ответ системы
        
        Returns:
            Тип эмоции
        """
        msg_lower = user_message.lower()
        
        # Определяем эмоцию по сообщению пользователя
        if any(w in msg_lower for w in ["спасибо", "благодар", "отлично", "прекрасно"]):
            return "joy"
        
        if any(w in msg_lower for w in ["проблема", "ошибка", "не работает", "сломал"]):
            return "sadness"
        
        if any(w in msg_lower for w in ["почему", "зачем", "как так", "несправедливо"]):
            return "anger"
        
        if any(w in msg_lower for w in ["что", "как", "расскажи", "объясни"]):
            return "curious"
        
        if any(w in msg_lower for w in ["неожиданно", "удивительно", "впервые"]):
            return "surprise"
        
        if any(w in msg_lower for w in ["правда", "точно", "уверен", "факт"]):
            # Проверяем уверенность в ответе
            if "возможно" in response.lower() or "не уверен" in response.lower():
                return "uncertain"
            return "confident"
        
        return "neutral"
    
    def configure(self, use_random_prefixes: Optional[bool] = None, 
                  max_prefix_length: Optional[int] = None):
        """
        Настройка движка
        
        Args:
            use_random_prefixes: Использовать ли случайные префиксы
            max_prefix_length: Максимальная длина префикса
        """
        if use_random_prefixes is not None:
            self.use_random_prefixes = use_random_prefixes
        if max_prefix_length is not None:
            self.max_prefix_length = max_prefix_length
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "use_random_prefixes": self.use_random_prefixes,
            "max_prefix_length": self.max_prefix_length,
            "available_emotions": list(self.tone_map.keys()),
            "version": "1.0"
        }


# ============================================================================
# ИНТЕГРАЦИЯ С PAD МОДЕЛЬЮ
# ============================================================================

def apply_emotional_tone(text: str, pad_model=None, 
                         user_message: str = "", 
                         meta: Optional[Dict[str, Any]] = None) -> str:
    """
    Применяет эмоциональный тон с использованием PAD модели
    
    Args:
        text: Исходный текст
        pad_model: Экземпляр PAD модели (если None, будет создан)
        user_message: Сообщение пользователя (для контекста)
        meta: Дополнительные мета-данные
    
    Returns:
        Текст с применённым тоном
    """
    engine = ToneEngine()
    
    if pad_model:
        # Используем PAD модель
        state = pad_model.get_state()
        pad_state = state.to_dict()
        return engine.apply_from_pad(text, pad_state, meta)
    else:
        # Используем контекст диалога
        if meta and "emotion" in meta:
            return engine.apply(text, meta["emotion"], meta)
        elif user_message:
            emotion = engine.get_emotion_from_context(user_message, text)
            return engine.apply(text, emotion, meta)
        else:
            return engine.apply(text, "neutral", meta)


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_tone_engine: Optional[ToneEngine] = None


def get_tone_engine() -> ToneEngine:
    """Возвращает глобальный ToneEngine"""
    global _tone_engine
    if _tone_engine is None:
        _tone_engine = ToneEngine()
    return _tone_engine


def reset_tone_engine():
    """Сбрасывает глобальный ToneEngine (для тестов)"""
    global _tone_engine
    _tone_engine = None