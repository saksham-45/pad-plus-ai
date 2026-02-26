# Система Эмоций

Этот документ описывает систему эмоций в PAD+ AI.

## Обзор

Система эмоций реализует PAD+ модель эмоций, которая включает:

- Трехмерную модель эмоций (Pleasure, Arousal, Dominance)
- Дополнительные эмоциональные параметры
- Динамическое изменение эмоций
- Интеграцию с коммуникацией
- Эмоциональную память

## PAD+ Модель

### Основные измерения

```python
PAD_DIMENSIONS = {
    "удовольствие": {
        "description": "Уровень удовольствия/дискомфорта",
        "range": (-1.0, 1.0),
        "low": "дискомфорт, боль, неприятие",
        "high": "удовольствие, радость, удовлетворение"
    },
    "возбуждение": {
        "description": "Уровень активации/пассивности",
        "range": (0.0, 1.0),
        "low": "спокойствие, расслабленность, сонливость",
        "high": "возбуждение, активность, энергия"
    },
    "доминирование": {
        "description": "Чувство контроля/подчинения",
        "range": (-1.0, 1.0),
        "low": "подчинение, беспомощность, зависимость",
        "high": "контроль, власть, независимость"
    }
}
```

### Дополнительные параметры

```python
ADDITIONAL_EMOTIONS = {
    "любопытство": {
        "description": "Интерес к новому опыту",
        "range": (0.0, 1.0),
        "influence": "стимулирует обучение и исследование"
    },
    "уверенность": {
        "description": "Уверенность в своих действиях",
        "range": (0.0, 1.0),
        "influence": "влияет на принятие решений"
    },
    "социальная_связь": {
        "description": "Желание социального взаимодействия",
        "range": (0.0, 1.0),
        "influence": "регулирует коммуникативное поведение"
    }
}
```

## EmotionManager (core/emotion.py)

### Центральный менеджер эмоций

```python
class EmotionManager:
    def __init__(self):
        self.state = self.initialize_emotion_state()
        self.emotion_history = []
        self.emotion_triggers = {}
        self.emotion_regulators = {}
        self.style = self.initialize_style()
        
    def initialize_emotion_state(self) -> dict:
        """Инициализация начального эмоционального состояния"""
        return {
            # Основные PAD параметры
            "удовольствие": 0.5,      # Нейтральное удовольствие
            "возбуждение": 0.3,       # Умеренное возбуждение
            "доминирование": 0.5,      # Средний контроль
            
            # Дополнительные параметры
            "любопытство": 0.5,       # Умеренное любопытство
            "уверенность": 0.5,       # Средняя уверенность
            "социальная_связь": 0.3,  # Низкая социальная потребность
            
            # Вторичные эмоции (производные)
            "интерес": 0.0,
            "удивление": 0.0,
            "раздражение": 0.0,
            "тревога": 0.0
        }
        
    def initialize_style(self) -> dict:
        """Инициализация стиля коммуникации"""
        return {
            "tone": "neutral",
            "verbosity": "medium",
            "color": "blue",
            "formality": "medium"
        }
```

### Обновление эмоционального состояния

```python
def update_state(self, response: str, context: dict):
    """Обновление эмоционального состояния"""
    # 1. Анализ текста ответа
    text_analysis = self.analyze_text_emotions(response)
    
    # 2. Анализ контекста
    context_analysis = self.analyze_context_emotions(context)
    
    # 3. Расчет изменений
    emotion_changes = self.calculate_emotion_changes(text_analysis, context_analysis)
    
    # 4. Применение изменений
    self.apply_emotion_changes(emotion_changes)
    
    # 5. Обновление стиля
    self.update_style()
    
    # 6. Сохранение в историю
    self.save_to_history()
    
    # 7. Рассылка через WebSocket
    asyncio.create_task(self.broadcast_emotion_update())
    
def analyze_text_emotions(self, text: str) -> dict:
    """Анализ эмоций в тексте"""
    # Использование NLP для анализа тона
    sentiment = self.analyze_sentiment(text)
    
    # Анализ эмоциональных слов
    emotion_words = self.extract_emotion_words(text)
    
    # Анализ интенсивности
    intensity = self.calculate_intensity(text)
    
    return {
        "sentiment": sentiment,
        "emotion_words": emotion_words,
        "intensity": intensity
    }
    
def analyze_context_emotions(self, context: dict) -> dict:
    """Анализ эмоций в контексте"""
    return {
        "user_emotion": context.get("user_emotion", {}),
        "interaction_history": context.get("interaction_history", []),
        "current_task": context.get("current_task", {}),
        "time_of_day": context.get("time_of_day", datetime.now())
    }
```

### Расчет изменений эмоций

```python
def calculate_emotion_changes(self, text_analysis: dict, context_analysis: dict) -> dict:
    """Расчет изменений эмоционального состояния"""
    changes = {}
    
    # Изменение удовольствия
    changes["удовольствие"] = self.calculate_pleasure_change(text_analysis, context_analysis)
    
    # Изменение возбуждения
    changes["возбуждение"] = self.calculate_arousal_change(text_analysis, context_analysis)
    
    # Изменение доминирования
    changes["доминирование"] = self.calculate_dominance_change(text_analysis, context_analysis)
    
    # Изменение любопытства
    changes["любопытство"] = self.calculate_curiosity_change(text_analysis, context_analysis)
    
    # Изменение уверенности
    changes["уверенность"] = self.calculate_confidence_change(text_analysis, context_analysis)
    
    # Изменение социальной связи
    changes["социальная_связь"] = self.calculate_social_change(text_analysis, context_analysis)
    
    return changes
    
def calculate_pleasure_change(self, text_analysis: dict, context_analysis: dict) -> float:
    """Расчет изменения удовольствия"""
    sentiment = text_analysis["sentiment"]
    intensity = text_analysis["intensity"]
    
    # Позитивный сильный ответ повышает удовольствие
    if sentiment > 0.5 and intensity > 0.7:
        return 0.2 * intensity
        
    # Негативный ответ понижает удовольствие
    elif sentiment < -0.5:
        return -0.15 * abs(sentiment)
        
    # Нейтральный ответ - небольшое изменение
    else:
        return 0.05 * sentiment
```

## Эмоциональные триггеры

### Система триггеров

```python
class EmotionTriggers:
    def __init__(self, emotion_manager: EmotionManager):
        self.emotion_manager = emotion_manager
        self.triggers = self.load_triggers()
        
    def load_triggers(self) -> dict:
        """Загрузка эмоциональных триггеров"""
        return {
            "positive_feedback": {
                "keywords": ["спасибо", "хорошо", "отлично", "молодец"],
                "effect": {"удовольствие": 0.3, "уверенность": 0.2}
            },
            "negative_feedback": {
                "keywords": ["плохо", "неправильно", "глупо", "ошибся"],
                "effect": {"удовольствие": -0.3, "уверенность": -0.2}
            },
            "complex_question": {
                "keywords": ["почему", "как", "объясни", "докажи"],
                "effect": {"любопытство": 0.4, "возбуждение": 0.2}
            },
            "emotional_topic": {
                "keywords": ["грусть", "радость", "страх", "любовь"],
                "effect": {"социальная_связь": 0.3, "эмпатия": 0.4}
            }
        }
        
    def check_triggers(self, text: str) -> dict:
        """Проверка срабатывания триггеров"""
        triggered_effects = {}
        
        for trigger_name, trigger_data in self.triggers.items():
            if self.trigger_matches(text, trigger_data["keywords"]):
                for emotion, effect in trigger_data["effect"].items():
                    if emotion in triggered_effects:
                        triggered_effects[emotion] += effect
                    else:
                        triggered_effects[emotion] = effect
                        
        return triggered_effects
        
    def trigger_matches(self, text: str, keywords: list) -> bool:
        """Проверка совпадения триггера"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
```

## Эмоциональная регуляция

### Система регуляции

```python
class EmotionRegulators:
    def __init__(self, emotion_manager: EmotionManager):
        self.emotion_manager = emotion_manager
        self.regulation_strategies = self.load_strategies()
        
    def load_strategies(self) -> dict:
        """Загрузка стратегий регуляции"""
        return {
            "cognitive_reappraisal": {
                "description": "Когнитивная переоценка",
                "trigger_conditions": {"тревога": 0.7, "раздражение": 0.6},
                "effects": {"тревога": -0.3, "раздражение": -0.3, "уверенность": 0.2}
            },
            "distraction": {
                "description": "Отвлечение внимания",
                "trigger_conditions": {"тревога": 0.8, "раздражение": 0.8},
                "effects": {"возбуждение": -0.4, "тревога": -0.2}
            },
            "social_engagement": {
                "description": "Социальное взаимодействие",
                "trigger_conditions": {"социальная_связь": 0.8},
                "effects": {"социальная_связь": -0.3, "удовольствие": 0.2}
            }
        }
        
    def apply_regulation(self):
        """Применение стратегий регуляции"""
        current_state = self.emotion_manager.get_state()
        
        for strategy_name, strategy_data in self.regulation_strategies.items():
            if self.should_apply_strategy(current_state, strategy_data):
                self.apply_strategy_effects(strategy_data["effects"])
                
    def should_apply_strategy(self, state: dict, strategy_data: dict) -> bool:
        """Проверка необходимости применения стратегии"""
        trigger_conditions = strategy_data["trigger_conditions"]
        
        for emotion, threshold in trigger_conditions.items():
            if state.get(emotion, 0.0) >= threshold:
                return True
                
        return False
```

## Стиль коммуникации

### Эмоциональный стиль

```python
def update_style(self):
    """Обновление стиля коммуникации на основе эмоций"""
    current_state = self.state
    
    # Определение тона
    self.style["tone"] = self.determine_tone(current_state)
    
    # Определение verbosity
    self.style["verbosity"] = self.determine_verbosity(current_state)
    
    # Определение цвета
    self.style["color"] = self.determine_color(current_state)
    
    # Определение формальности
    self.style["formality"] = self.determine_formality(current_state)
    
def determine_tone(self, state: dict) -> str:
    """Определение тона коммуникации"""
    pleasure = state["удовольствие"]
    arousal = state["возбуждение"]
    confidence = state["уверенность"]
    
    if pleasure > 0.8 and arousal > 0.7:
        return "enthusiastic"
    elif pleasure > 0.6 and confidence > 0.7:
        return "confident"
    elif pleasure < 0.3 and arousal > 0.6:
        return "frustrated"
    elif pleasure < 0.3 and arousal < 0.4:
        return "depressed"
    elif state["социальная_связь"] > 0.7:
        return "warm"
    else:
        return "neutral"
        
def determine_verbosity(self, state: dict) -> str:
    """Определение verbosity"""
    arousal = state["возбуждение"]
    curiosity = state["любопытство"]
    
    if arousal > 0.8 or curiosity > 0.8:
        return "high"
    elif arousal < 0.3 and curiosity < 0.3:
        return "low"
    else:
        return "medium"
```

### Цветовая ассоциация

```python
def determine_color(self, state: dict) -> str:
    """Определение цветовой ассоциации"""
    pleasure = state["удовольствие"]
    arousal = state["возбуждение"]
    
    if pleasure > 0.8 and arousal > 0.6:
        return "yellow"  # Радость, энергия
    elif pleasure > 0.6 and arousal < 0.4:
        return "green"   # Спокойствие, гармония
    elif pleasure < 0.3 and arousal > 0.6:
        return "red"     # Гнев, активность
    elif pleasure < 0.3 and arousal < 0.4:
        return "blue"    # Грусть, спокойствие
    elif state["любопытство"] > 0.8:
        return "purple"  # Творчество, загадочность
    else:
        return "blue"    # Нейтральный
```

## Эмоциональная память

### Хранение эмоциональных воспоминаний

```python
class EmotionMemory:
    def __init__(self, emotion_manager: EmotionManager):
        self.emotion_manager = emotion_manager
        self.emotional_memories = []
        
    def store_emotional_memory(self, trigger: str, emotion_state: dict, response: str):
        """Сохранение эмоционального воспоминания"""
        memory = {
            "timestamp": datetime.now(),
            "trigger": trigger,
            "emotion_state": emotion_state.copy(),
            "response": response,
            "valence": self.calculate_valence(emotion_state),
            "intensity": self.calculate_intensity(emotion_state)
        }
        
        self.emotional_memories.append(memory)
        
        # Ограничение размера памяти
        if len(self.emotional_memories) > 1000:
            self.emotional_memories.pop(0)
            
    def get_similar_emotions(self, current_state: dict, threshold: float = 0.7) -> list:
        """Получение похожих эмоциональных состояний"""
        similar_memories = []
        
        for memory in self.emotional_memories:
            similarity = self.calculate_emotion_similarity(current_state, memory["emotion_state"])
            
            if similarity > threshold:
                similar_memories.append({
                    "memory": memory,
                    "similarity": similarity
                })
                
        return sorted(similar_memories, key=lambda x: x["similarity"], reverse=True)
        
    def calculate_emotion_similarity(self, state1: dict, state2: dict) -> float:
        """Расчет схожести эмоциональных состояний"""
        emotions = ["удовольствие", "возбуждение", "доминирование", "любопытство"]
        
        similarities = []
        for emotion in emotions:
            if emotion in state1 and emotion in state2:
                diff = abs(state1[emotion] - state2[emotion])
                similarity = 1.0 - diff
                similarities.append(similarity)
                
        return sum(similarities) / len(similarities) if similarities else 0.0
```

## Интеграция с коммуникацией

### Эмоциональная модуляция ответов

```python
def modulate_response(self, base_response: str, context: dict) -> str:
    """Модуляция ответа на основе эмоционального состояния"""
    current_state = self.get_state()
    
    # 1. Эмоциональная окраска
    modulated_response = self.add_emotional_color(base_response, current_state)
    
    # 2. Адаптация стиля
    modulated_response = self.apply_style_modulation(modulated_response, context)
    
    # 3. Добавление эмоциональных маркеров
    modulated_response = self.add_emotional_markers(modulated_response, current_state)
    
    return modulated_response
    
def add_emotional_color(self, response: str, state: dict) -> str:
    """Добавление эмоциональной окраски к ответу"""
    tone = self.style["tone"]
    
    if tone == "enthusiastic":
        response = "Отличный вопрос! " + response
    elif tone == "warm":
        response = "Я понимаю, что вы имеете в виду. " + response
    elif tone == "frustrated":
        response = "Честно говоря, это довольно сложно... " + response
    elif tone == "depressed":
        response = "Ну, как бы это сказать... " + response
        
    return response
    
def add_emotional_markers(self, response: str, state: dict) -> str:
    """Добавление эмоциональных маркеров"""
    markers = []
    
    if state["удовольствие"] > 0.8:
        markers.append("😊")
    elif state["удовольствие"] < 0.3:
        markers.append("😔")
        
    if state["возбуждение"] > 0.8:
        markers.append("⚡")
    elif state["возбуждение"] < 0.3:
        markers.append("😴")
        
    if state["уверенность"] > 0.8:
        markers.append("💪")
    elif state["уверенность"] < 0.3:
        markers.append("🤔")
        
    if markers:
        response += " " + "".join(markers)
        
    return response
```

## Future улучшения

### Планы развития

1. **Advanced Emotion Recognition**
   - Распознавание эмоций пользователя
   - Анализ тона голоса (для голосовых интерфейсов)
   - Распознавание эмоций по тексту

2. **Emotion Prediction**
   - Прогнозирование эмоциональных состояний
   - Предиктивная регуляция
   - Проактивное управление настроением

3. **Cross-modal Emotions**
   - Интеграция с визуальными эмоциями
   - Эмоции в мультимодальных интерфейсах
   - Эмоциональная синестезия

4. **Cultural Adaptation**
   - Адаптация к культурным особенностям
   - Разные эмоциональные нормы
   - Локализация эмоциональных выражений

5. **Long-term Emotional Development**
   - Эмоциональное развитие во времени
   - Формирование эмоционального характера
   - Эмоциональная зрелость