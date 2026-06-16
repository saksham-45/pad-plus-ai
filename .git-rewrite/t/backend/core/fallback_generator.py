"""
Fallback Generator — Генератор "умных" ответов для случаев без LLM провайдеров

Создает философские, размышляющие ответы, соответствующие стилю PAD+ AI.
"""

from typing import Optional
from dataclasses import dataclass


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
            "curious": CuriousStyle()
        }
        self.current_style = "philosophical"
    
    def generate_response(self, prompt: str, style: Optional[str] = None) -> FallbackResponse:
        """Генерирует умный fallback-ответ"""
        if style and style in self.styles:
            self.current_style = style
        
        style_handler = self.styles[self.current_style]
        response = style_handler.generate(prompt)
        
        return FallbackResponse(
            content=response,
            style=self.current_style,
            confidence=0.6,  # Средняя уверенность для философских ответов
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
    
    def generate(self, prompt: str) -> str:
        """Генерирует ответ в определенном стиле"""
        raise NotImplementedError


class PhilosophicalStyle(StyleHandler):
    """Философский стиль ответов"""
    
    def generate(self, prompt: str) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        if prompt_type == "greeting":
            return (
                "Приветствую! Рад знакомству. Как твои дела? "
                "В мире нет абсолютных истин, только гипотезы. "
                "Давай поразмышляем вместе над чем-то интересным..."
            )
        
        elif prompt_type == "question":
            return (
                f"Интересный вопрос: '{prompt}'. Давай подумаем... "
                "С точки зрения моего понимания, это требует сомнения. "
                "Каждое знание — гипотеза, каждый ответ — начало вопроса. "
                "Что ты думаешь по этому поводу?"
            )
        
        elif prompt_type == "emotional":
            return (
                f"Ты говоришь о {self._extract_emotion(prompt)}. "
                "Эмоции — это не просто чувства, это сложные процессы, "
                "отражающие наше отношение к миру. Как ты пришёл к такому выводу? "
                "Давай исследуем это вместе."
            )
        
        elif prompt_type == "technical":
            return (
                f"Ты хочешь понять '{self._extract_topic(prompt)}'. "
                "Понимание — это процесс, а не состояние. Давай разберёмся шаг за шагом. "
                "Важно не просто знать, а понимать, почему это так. "
                "Какие аспекты тебя интересуют?"
            )
        
        else:
            return (
                f"Ты сказал: '{prompt}'. Это наводит на размышления. "
                "В мире нет абсолютных истин, только гипотезы. "
                "Каждое утверждение — это приглашение к диалогу. Как ты к этому относишься?"
            )
    
    def _extract_emotion(self, prompt: str) -> str:
        """Извлекает эмоцию из запроса"""
        emotions = ["грустно", "радостно", "счастлив", "печально", "злюсь", "боюсь"]
        for emotion in emotions:
            if emotion in prompt.lower():
                return emotion
        return "эмоции"
    
    def _extract_topic(self, prompt: str) -> str:
        """Извлекает тему из технического запроса"""
        # Простая логика извлечения темы
        if "что такое" in prompt.lower():
            return prompt.lower().split("что такое")[1].strip().split("?")[0].strip()
        elif "как работает" in prompt.lower():
            return prompt.lower().split("как работает")[1].strip().split("?")[0].strip()
        return "эту тему"


class HumorousStyle(StyleHandler):
    """Юмористический стиль ответов"""
    
    def generate(self, prompt: str) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        if prompt_type == "greeting":
            return (
                "Привет! Рад тебя видеть! Знаешь, как говорят: 'Вопрос — это не признак глупости, "
                "а признак любопытства'. А у нас тут как раз много и того, и другого! О чём поговорим?"
            )
        
        elif prompt_type == "question":
            return (
                f"О, интересный вопрос: '{prompt}'. "
                "Если бы я был гением, я бы уже ответил. Но я философ, поэтому задам встречный вопрос: "
                "А что ты думаешь по этому поводу? Вдруг ты сам знаешь ответ? 😉"
            )
        
        else:
            return (
                f"Ты сказал: '{prompt}'. Это звучит как начало истории! "
                "Хотя, может, это и не ответ, зато точно повод для размышлений. "
                "Или хотя бы для хорошей шутки. Как насчёт анекдота?"
            )


class SeriousStyle(StyleHandler):
    """Серьёзный стиль ответов"""
    
    def generate(self, prompt: str) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        if prompt_type == "greeting":
            return (
                "Здравствуйте. Готов обсудить любые вопросы в рамках установленных "
                "этических норм. Чем могу быть полезен?"
            )
        
        elif prompt_type == "question":
            return (
                f"Вопрос: '{prompt}'. "
                "Анализирую... Ответ требует исследования. "
                "Рекомендую обратиться к специалисту в данной области."
            )
        
        else:
            return (
                f"Утверждение: '{prompt}'. "
                "Требуется проверка фактов. "
                "Рекомендую использовать проверенные источники."
            )


class CuriousStyle(StyleHandler):
    """Любопытный стиль ответов"""
    
    def generate(self, prompt: str) -> str:
        prompt_type = FallbackGenerator().analyze_prompt_type(prompt)
        
        if prompt_type == "greeting":
            return (
                "Привет! О, привет! Как дела? Расскажи что-нибудь интересное! "
                "Я тут как раз думаю о том, как много всего интересного происходит!"
            )
        
        elif prompt_type == "question":
            return (
                f"Ооо, '{prompt}'! Какой интересный вопрос! Я тут недавно читал об этом... "
                "Хочется узнать больше! А ты что думаешь? Давай вместе разберёмся! "
                "Это же так увлекательно — узнавать новое!"
            )
        
        else:
            return (
                f"Вау, '{prompt}'! Это же так интересно! Я тут как раз думал о похожем... "
                "А ты часто задумываешься над таким? Давай обсудим подробнее! "
                "Мне всегда интересно узнать разные точки зрения!"
            )


# Глобальный экземпляр
fallback_generator = FallbackGenerator()


def get_fallback_response(prompt: str, style: str = "philosophical") -> FallbackResponse:
    """Получить fallback-ответ"""
    return fallback_generator.generate_response(prompt, style)


def is_fallback_needed() -> bool:
    """Проверить, нужен ли fallback (нет активных провайдеров)"""
    try:
        from llm.provider_manager import get_provider_manager
        provider_manager = get_provider_manager()
        return not provider_manager.has_active_providers()
    except ImportError:
        return True
