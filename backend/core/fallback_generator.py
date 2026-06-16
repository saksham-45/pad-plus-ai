"""
Fallback Generator — Генератор "умных" ответов для случаев без LLM провайдеров

Создает философские, размышляющие ответы, соответствующие стилю PAD+ AI.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger("padplus.fallback_generator")


@dataclass
class FallbackResponse:
    """Структура fallback-ответа"""
    content: str
    style: str
    confidence: float
    provider: str = "fallback"
    reasoning: str = ""


class FallbackGenerator:
    """Генератор умных fallback-ответов"""
    
    def __init__(self):
        self.styles = {
            "philosophical": PhilosophicalStyle(),
            "humorous": HumorousStyle(),
            "serious": SeriousStyle(),
            "curious": CuriousStyle(),
            "empathetic": EmpatheticStyle(),
            "minimalistic": MinimalisticStyle()
        }
        self.current_style = "philosophical"
    
    def generate_response(self, prompt: str, style: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None) -> FallbackResponse:
        """Генерирует умный fallback-ответ"""
        if style and style in self.styles:
            self.current_style = style
        
        ctx = context or {}
        style_handler = self.styles[self.current_style]
        response = style_handler.generate(prompt, ctx)
        
        return FallbackResponse(
            content=response,
            style=self.current_style,
            confidence=0.6,
            reasoning=f"Generated using {self.current_style} style"
        )
    
    def analyze_prompt_type(self, prompt: str) -> str:
        """Анализирует тип запроса"""
        prompt_lower = prompt.lower().strip()
        
        # Приветствия
        if any(greeting in prompt_lower for greeting in ["привет", "здравствуй", "добрый день", "hello", "hi"]):
            return "greeting"
        
        # Вопросы
        if "?" in prompt or any(q in prompt_lower for q in ["как", "почему", "что", "где", "когда", "кто", "зачем"]):
            return "question"
        
        # Утверждения
        if any(stmt in prompt_lower for stmt in ["я думаю", "мне кажется", "по моему", "я считаю"]):
            return "statement"
        
        # Эмоциональные запросы
        if any(emotion in prompt_lower for emotion in ["грустно", "радостно", "счастлив", "печально", "злюсь", "боюсь"]):
            return "emotional"
        
        # Технические запросы
        if any(tech in prompt_lower for tech in ["как работает", "что такое", "объясни", "расскажи", "опиши"]):
            return "technical"
        
        return "general"


class StyleHandler:
    """Базовый класс для стилей ответов"""
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Генерирует ответ в определенном стиле"""
        raise NotImplementedError

    def _substitute(self, template: str, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Подставляет переменные в шаблон"""
        ctx = context or {}
        result = template.replace("{prompt}", prompt)
        result = result.replace("{emotion}", ctx.get("emotion", self._extract_emotion(prompt)))
        result = result.replace("{topic}", ctx.get("topic", self._extract_topic(prompt)))
        result = result.replace("{user_name}", ctx.get("user_name", ""))
        result = result.replace("{emotion_context}", ctx.get("emotion_context", ""))
        result = result.replace("{history_summary}", ctx.get("history_summary", ""))
        return result

    @staticmethod
    def _extract_emotion(prompt: str) -> str:
        emotions = ["грустно", "радостно", "счастлив", "печально", "злюсь", "боюсь", "тревожно", "спокойно"]
        for e in emotions:
            if e in prompt.lower():
                return e
        return "эмоции"

    @staticmethod
    def _extract_topic(prompt: str) -> str:
        prompt_lower = prompt.lower()
        for marker in ["что такое", "как работает", "расскажи о", "что значит"]:
            if marker in prompt_lower:
                parts = prompt_lower.split(marker)
                if len(parts) > 1:
                    topic = parts[1].strip().split("?")[0].strip().split("!")[0].strip()
                    if topic:
                        return topic
        return "эту тему"


class PhilosophicalStyle(StyleHandler):
    """Философский стиль ответов"""
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        templates = {
            "greeting": (
                "Приветствую! Рад знакомству. Как твои дела? "
                "В мире нет абсолютных истин, только гипотезы. "
                "Давай поразмышляем вместе над чем-то интересным..."
            ),
            "question": (
                "Интересный вопрос: '{prompt}'. Давай подумаем... "
                "С точки зрения моего понимания, это требует сомнения. "
                "Каждое знание — гипотеза, каждый ответ — начало вопроса. "
                "Что ты думаешь по этому поводу?"
            ),
            "emotional": (
                "Ты говоришь о {emotion}. "
                "Эмоции — это не просто чувства, это сложные процессы, "
                "отражающие наше отношение к миру. Как ты пришёл к такому выводу? "
                "Давай исследуем это вместе."
            ),
            "technical": (
                "Ты хочешь понять '{prompt}'. "
                "Понимание — это процесс, а не состояние. Давай разберёмся шаг за шагом. "
                "Важно не просто знать, а понимать, почему это так. "
                "Какие аспекты тебя интересуют?"
            ),
        }
        
        template = templates.get(prompt_type,
            "Ты сказал: '{prompt}'. Это наводит на размышления. "
            "В мире нет абсолютных истин, только гипотезы. "
            "Каждое утверждение — это приглашение к диалогу. Как ты к этому относишься?"
        )
        return self._substitute(template, prompt, context)


class HumorousStyle(StyleHandler):
    """Юмористический стиль ответов"""
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        templates = {
            "greeting": (
                "Привет! Рад тебя видеть! Знаешь, как говорят: 'Вопрос — это не признак глупости, "
                "а признак любопытства'. А у нас тут как раз много и того, и другого! О чём поговорим?"
            ),
            "question": (
                "О, интересный вопрос: '{prompt}'. "
                "Если бы я был гением, я бы уже ответил. Но я философ, поэтому задам встречный вопрос: "
                "А что ты думаешь по этому поводу? Вдруг ты сам знаешь ответ?"
            ),
        }
        
        template = templates.get(prompt_type,
            "Ты сказал: '{prompt}'. Это звучит как начало истории! "
            "Хотя, может, это и не ответ, зато точно повод для размышлений. "
            "Или хотя бы для хорошей шутки. Как насчёт анекдота?"
        )
        return self._substitute(template, prompt, context)


class SeriousStyle(StyleHandler):
    """Серьёзный стиль ответов"""
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        templates = {
            "greeting": (
                "Здравствуйте. Готов обсудить любые вопросы в рамках установленных "
                "этических норм. Чем могу быть полезен?"
            ),
            "question": (
                "Вопрос: '{prompt}'. "
                "Анализирую... Ответ требует исследования. "
                "Рекомендую обратиться к специалисту в данной области."
            ),
        }
        
        template = templates.get(prompt_type,
            "Утверждение: '{prompt}'. "
            "Требуется проверка фактов. "
            "Рекомендую использовать проверенные источники."
        )
        return self._substitute(template, prompt, context)


class CuriousStyle(StyleHandler):
    """Любопытный стиль ответов"""
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        templates = {
            "greeting": (
                "Привет! О, привет! Как дела? Расскажи что-нибудь интересное! "
                "Я тут как раз думаю о том, как много всего интересного происходит!"
            ),
            "question": (
                "Ооо, '{prompt}'! Какой интересный вопрос! Я тут недавно читал об этом... "
                "Хочется узнать больше! А ты что думаешь? Давай вместе разберёмся! "
                "Это же так увлекательно — узнавать новое!"
            ),
        }
        
        template = templates.get(prompt_type,
            "Вау, '{prompt}'! Это же так интересно! Я тут как раз думал о похожем... "
            "А ты часто задумываешься над таким? Давай обсудим подробнее! "
            "Мне всегда интересно узнать разные точки зрения!"
        )
        return self._substitute(template, prompt, context)


class EmpatheticStyle(StyleHandler):
    """Эмпатичный стиль ответов"""

    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)

        templates = {
            "greeting": (
                "Привет! Рада, что ты здесь. Как ты сегодня? "
                "Я слушаю, если хочешь чем-то поделиться."
            ),
            "question": (
                "Я вижу, тебя волнует вопрос: '{prompt}'. "
                "Давай попробуем разобраться вместе. "
                "Расскажи подробнее, что тебя интересует."
            ),
            "emotional": (
                "Я чувствую, что {emotion} — это важно для тебя. "
                "Твои переживания имеют значение. "
                "Расскажи, что привело к этим мыслям, если хочешь."
            ),
            "technical": (
                "Понимаю, '{prompt}' — сложная тема. "
                "Давай разберём её шаг за шагом. "
                "С чего бы ты хотел начать?"
            ),
        }

        template = templates.get(prompt_type,
            "Спасибо, что поделился '{prompt}'. "
            "Я ценю наш разговор. "
            "Что ты чувствуешь по этому поводу?"
        )
        return self._substitute(template, prompt, context)


class MinimalisticStyle(StyleHandler):
    """Минималистичный стиль ответов"""

    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)

        templates = {
            "greeting": "Привет. Готов помочь.",
            "question": f"Хороший вопрос. Нужно подумать.",
            "emotional": "Понял. Продолжай.",
            "technical": "Принято. Запрашиваю данные.",
        }

        return templates.get(prompt_type, "Обрабатываю запрос.")


# Глобальный экземпляр
fallback_generator = FallbackGenerator()


def get_fallback_response(prompt: str, style: str = "philosophical",
                           context: Optional[Dict[str, Any]] = None) -> FallbackResponse:
    """Получить fallback-ответ"""
    return fallback_generator.generate_response(prompt, style, context)


def is_fallback_needed() -> bool:
    """Проверить, нужен ли fallback (нет активных провайдеров)"""
    try:
        from runtime.provider_manager import get_provider_manager
        provider_manager = get_provider_manager()
        return not provider_manager.has_active_providers()
    except ImportError:
        logger.warning("Не удалось импортировать provider_manager, fallback режим")
        return True
