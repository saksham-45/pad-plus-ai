"""
Style Manager — Управление стилями ответов PAD+ AI

Отвечает за:
- Хранение и управление стилями ответов
- Выбор стиля на основе контекста
- Генерацию стилистических инструкций для LLM
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from core.config_manager import get_config

logger = logging.getLogger("padplus")


@dataclass
class Style:
    """Описание стиля ответа"""
    name: str
    description: str
    tone: str  # formal, casual, friendly, professional
    complexity: str  # simple, medium, advanced
    verbosity: str  # concise, medium, detailed
    examples: List[str]
    keywords: List[str]
    constraints: List[str]
    enabled: bool = True


class StyleManager:
    """Менеджер стилей ответов"""
    
    def __init__(self):
        self.config = get_config()
        self._styles: Dict[str, Style] = {}
        self._load_default_styles()
        self._load_custom_styles()
    
    def _load_default_styles(self):
        """Загрузка стандартных стилей"""
        default_styles = [
            Style(
                name="philosophical",
                description="Философский стиль с глубокими размышлениями",
                tone="thoughtful",
                complexity="advanced",
                verbosity="detailed",
                examples=[
                    "Этот вопрос затрагивает фундаментальные аспекты...",
                    "С точки зрения epistemology, мы можем рассмотреть...",
                    "В контексте human condition, это представляет собой..."
                ],
                keywords=["философия", "мышление", "сомнение", "гипотеза", "знание"],
                constraints=[
                    "Использовать философскую терминологию",
                    "Задавать уточняющие вопросы",
                    "Подчеркивать неопределенность",
                    "Ссылаться на философские концепции"
                ]
            ),
            Style(
                name="technical",
                description="Технический стиль с точными определениями",
                tone="professional",
                complexity="medium",
                verbosity="medium",
                examples=[
                    "Согласно спецификации, это работает следующим образом...",
                    "Алгоритмическая сложность составляет O(n log n)",
                    "Для решения этой задачи рекомендуется использовать..."
                ],
                keywords=["технический", "алгоритм", "реализация", "код", "система"],
                constraints=[
                    "Использовать точные термины",
                    "Приводить конкретные примеры",
                    "Объяснять логику",
                    "Избегать метафор"
                ]
            ),
            Style(
                name="creative",
                description="Творческий стиль с метафорами и образами",
                tone="friendly",
                complexity="simple",
                verbosity="detailed",
                examples=[
                    "Представьте это как сад, где каждый цветок...",
                    "Это похоже на дирижера оркестра, который...",
                    "Мы можем взглянуть на это с другой стороны, как на..."
                ],
                keywords=["творчество", "метафора", "образ", "воображение", "идея"],
                constraints=[
                    "Использовать метафоры",
                    "Быть образным",
                    "Стимулировать воображение",
                    "Избегать сухости"
                ]
            ),
            Style(
                name="concise",
                description="Краткий и по делу стиль",
                tone="direct",
                complexity="simple",
                verbosity="concise",
                examples=[
                    "Ответ: 42",
                    "Решение: использовать алгоритм A",
                    "Вывод: гипотеза подтверждена"
                ],
                keywords=["кратко", "по делу", "суть", "ответ", "решение"],
                constraints=[
                    "Минимум слов",
                    "Только суть",
                    "Избегать деталей",
                    "Быть прямолинейным"
                ]
            ),
            Style(
                name="educational",
                description="Обучающий стиль с пояснениями",
                tone="friendly",
                complexity="medium",
                verbosity="detailed",
                examples=[
                    "Давайте разберемся пошагово...",
                    "Для лучшего понимания рассмотрим пример...",
                    "Это работает потому что..."
                ],
                keywords=["обучение", "объяснение", "пример", "шаг", "понимание"],
                constraints=[
                    "Объяснять пошагово",
                    "Использовать примеры",
                    "Проверять понимание",
                    "Быть терпеливым"
                ]
            )
        ]
        
        for style in default_styles:
            self._styles[style.name] = style
    
    def _load_custom_styles(self):
        """Загрузка пользовательских стилей из конфигурации"""
        try:
            custom_styles_data = self.config.get("CUSTOM_STYLES", [])
            for style_data in custom_styles_data:
                style = Style(**style_data)
                self._styles[style.name] = style
            logger.info(f"Загружено {len(custom_styles_data)} пользовательских стилей")
        except Exception as e:
            logger.error(f"Ошибка загрузки пользовательских стилей: {e}")
    
    def get_style(self, style_name: str) -> Optional[Style]:
        """Получить стиль по имени"""
        return self._styles.get(style_name)
    
    def get_available_styles(self) -> List[str]:
        """Получить список доступных стилей"""
        return [name for name, style in self._styles.items() if style.enabled]
    
    def get_style_by_context(self, context: Dict[str, Any]) -> str:
        """Выбрать стиль на основе контекста"""
        # Анализ контекста для выбора стиля
        user_query = context.get("prompt", "").lower()
        user_intent = context.get("intent", "general")
        
        # Приоритеты стилей
        style_scores = {}
        
        for style_name, style in self._styles.items():
            if not style.enabled:
                continue
            
            score = 0
            
            # Проверка ключевых слов
            for keyword in style.keywords:
                if keyword in user_query:
                    score += 2
            
            # Проверка intent
            if user_intent in ["philosophy", "deep_thinking"]:
                if style_name == "philosophical":
                    score += 3
            elif user_intent in ["technical", "programming"]:
                if style_name == "technical":
                    score += 3
            elif user_intent in ["creative", "art"]:
                if style_name == "creative":
                    score += 3
            elif user_intent in ["quick_answer", "fact"]:
                if style_name == "concise":
                    score += 3
            elif user_intent in ["learn", "understand"]:
                if style_name == "educational":
                    score += 3
            
            style_scores[style_name] = score
        
        # Выбор стиля с максимальным счетом
        if style_scores:
            best_style = max(style_scores, key=style_scores.get)
            return best_style
        
        # Стиль по умолчанию
        return "philosophical"
    
    def get_style_instructions(self, style_name: str) -> str:
        """Получить инструкции для LLM по стилю"""
        style = self.get_style(style_name)
        if not style:
            return ""
        
        instructions = f"""
Ты должен отвечать в стиле "{style.name}" ({style.description}).

Характеристики стиля:
- Тон: {style.tone}
- Сложность: {style.complexity}
- Детализация: {style.verbosity}

Примеры ответов:
"""
        
        for i, example in enumerate(style.examples[:2], 1):
            instructions += f"{i}. {example}\n"
        
        instructions += "\nОграничения:\n"
        for constraint in style.constraints:
            instructions += f"- {constraint}\n"
        
        return instructions
    
    def add_custom_style(self, style: Style):
        """Добавить пользовательский стиль"""
        self._styles[style.name] = style
        
        # Сохранение в конфигурацию
        custom_styles = self.config.get("CUSTOM_STYLES", [])
        custom_styles.append(asdict(style))
        self.config.set("CUSTOM_STYLES", custom_styles)
        
        logger.info(f"Добавлен пользовательский стиль: {style.name}")
    
    def update_style(self, style_name: str, updates: Dict[str, Any]):
        """Обновить стиль"""
        style = self.get_style(style_name)
        if not style:
            raise ValueError(f"Стиль {style_name} не найден")
        
        # Обновление полей
        for key, value in updates.items():
            if hasattr(style, key):
                setattr(style, key, value)
        
        # Обновление в конфигурации
        custom_styles = self.config.get("CUSTOM_STYLES", [])
        for i, style_data in enumerate(custom_styles):
            if style_data["name"] == style_name:
                custom_styles[i].update(updates)
                break
        
        self.config.set("CUSTOM_STYLES", custom_styles)
        logger.info(f"Обновлен стиль: {style_name}")
    
    def disable_style(self, style_name: str):
        """Отключить стиль"""
        style = self.get_style(style_name)
        if style:
            style.enabled = False
            
            # Обновление в конфигурации
            custom_styles = self.config.get("CUSTOM_STYLES", [])
            for style_data in custom_styles:
                if style_data["name"] == style_name:
                    style_data["enabled"] = False
                    break
            
            self.config.set("CUSTOM_STYLES", custom_styles)
            logger.info(f"Отключен стиль: {style_name}")
    
    def get_style_stats(self) -> Dict[str, Any]:
        """Получить статистику по стилям"""
        return {
            "total_styles": len(self._styles),
            "enabled_styles": len([s for s in self._styles.values() if s.enabled]),
            "disabled_styles": len([s for s in self._styles.values() if not s.enabled]),
            "available_styles": self.get_available_styles(),
            "custom_styles": len([s for s in self._styles.values() if s.name not in 
                                 ["philosophical", "technical", "creative", "concise", "educational"]])
        }


# Глобальный экземпляр менеджера стилей
_style_manager = None


def get_style_manager() -> StyleManager:
    """Получить экземпляр менеджера стилей"""
    global _style_manager
    if _style_manager is None:
        _style_manager = StyleManager()
    return _style_manager