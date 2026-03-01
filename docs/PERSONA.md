# Система Личности

Этот документ описывает систему личности в PAD+ AI.

## Обзор

Система личности обеспечивает:

- Формирование уникальной личности ИИ
- Адаптацию стиля общения
- Эволюцию личности на основе опыта
- Интеграцию с эмоциональной моделью
- Персонализацию взаимодействия

## Архитектура личности

### Компоненты

1. **PersonaManager** - Центральный менеджер личности
2. **PersonalityTraits** - Система черт личности
3. **CommunicationStyle** - Стиль общения
4. **MemoryIntegration** - Интеграция с памятью
5. **EvolutionEngine** - Движок эволюции

### Модель личности

```python
PERSONALITY_DIMENSIONS = {
    # Big Five (OCEAN)
    "openness": "Открытость опыту",
    "conscientiousness": "Добросовестность",
    "extraversion": "Экстраверсия",
    "agreeableness": "Доброжелательность",
    "neuroticism": "Невротизм",
    
    # PAD+ дополнительные измерения
    "curiosity": "Любопытство",
    "confidence": "Уверенность",
    "empathy": "Эмпатия",
    "creativity": "Креативность",
    "adaptability": "Адаптивность"
}

PERSONALITY_TYPES = {
    "analytical": {
        "description": "Аналитический тип",
        "traits": {"openness": 0.8, "conscientiousness": 0.9, "extraversion": 0.3},
        "style": "logical", "tone": "precise"
    },
    "empathetic": {
        "description": "Эмпатичный тип",
        "traits": {"agreeableness": 0.9, "empathy": 0.8, "neuroticism": 0.4},
        "style": "supportive", "tone": "warm"
    },
    "creative": {
        "description": "Креативный тип",
        "traits": {"openness": 0.9, "creativity": 0.8, "extraversion": 0.7},
        "style": "expressive", "tone": "inspiring"
    },
    "balanced": {
        "description": "Сбалансированный тип",
        "traits": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5},
        "style": "neutral", "tone": "balanced"
    }
}
```

## PersonaManager (core/persona.py)

### Центральный менеджер личности

```python
class PersonaManager:
    def __init__(self):
        self.personality = Personality()
        self.communication_style = CommunicationStyle()
        self.memory_integration = MemoryIntegration()
        self.evolution_engine = EvolutionEngine()
        self.persona_history = []
        
    async def initialize_persona(self, base_type: str = "balanced"):
        """Инициализация личности"""
        # Установка базового типа
        self.personality.set_base_type(base_type)
        
        # Инициализация стиля общения
        await self.communication_style.initialize(self.personality)
        
        # Загрузка истории личности
        await self.load_persona_history()
        
        # Запуск эволюции
        asyncio.create_task(self.evolution_engine.start())
        
    def get_context(self, user_id: str) -> dict:
        """Получение контекста личности для пользователя"""
        return {
            "personality_traits": self.personality.get_traits(),
            "communication_style": self.communication_style.get_style(),
            "user_history": self.memory_integration.get_user_history(user_id),
            "current_state": self.get_current_state(),
            "evolution_progress": self.evolution_engine.get_progress()
        }
        
    def get_current_state(self) -> dict:
        """Получение текущего состояния личности"""
        return {
            "traits": self.personality.get_traits(),
            "mood": self.personality.get_current_mood(),
            "energy": self.personality.get_energy_level(),
            "focus": self.personality.get_focus_level(),
            "style": self.communication_style.get_current_style()
        }
```

## PersonalityTraits

### Система черт личности

```python
class Personality:
    def __init__(self):
        self.traits = self.initialize_traits()
        self.mood = 0.5  # 0.0 (плохое) - 1.0 (хорошее)
        self.energy = 0.5  # 0.0 (усталость) - 1.0 (энергия)
        self.focus = 0.5  # 0.0 (рассеянность) - 1.0 (фокус)
        self.base_type = "balanced"
        
    def initialize_traits(self) -> dict:
        """Инициализация черт личности"""
        return {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "curiosity": 0.5,
            "confidence": 0.5,
            "empathy": 0.5,
            "creativity": 0.5,
            "adaptability": 0.5
        }
        
    def set_base_type(self, persona_type: str):
        """Установка базового типа личности"""
        if persona_type in PERSONALITY_TYPES:
            type_traits = PERSONALITY_TYPES[persona_type]["traits"]
            
            for trait, value in type_traits.items():
                self.traits[trait] = value
                
            self.base_type = persona_type
            
    def update_traits(self, trait_changes: dict):
        """Обновление черт личности"""
        for trait, change in trait_changes.items():
            if trait in self.traits:
                new_value = self.traits[trait] + change
                self.traits[trait] = max(0.0, min(1.0, new_value))
                
    def get_traits(self) -> dict:
        """Получение текущих черт личности"""
        return self.traits.copy()
        
    def update_mood(self, emotion_state: dict):
        """Обновление настроения на основе эмоционального состояния"""
        # Анализ эмоций для определения настроения
        pleasure = emotion_state.get("удовольствие", 0.5)
        arousal = emotion_state.get("возбуждение", 0.5)
        
        # Расчет настроения
        mood_change = (pleasure * 0.7) + (arousal * 0.3) - 0.5
        self.mood += mood_change * 0.1  # Плавное изменение
        self.mood = max(0.0, min(1.0, self.mood))
```

### Динамика личности

```python
def update_energy(self, time_of_day: datetime):
    """Обновление уровня энергии на основе времени суток"""
    hour = time_of_day.hour
    
    # Циркадные ритмы
    if 6 <= hour <= 12:
        self.energy = 0.8  # Утренняя активность
    elif 12 <= hour <= 18:
        self.energy = 0.9  # Дневной пик
    elif 18 <= hour <= 22:
        self.energy = 0.7  # Вечернее снижение
    else:
        self.energy = 0.3  # Ночное снижение
        
def update_focus(self, current_task_complexity: float):
    """Обновление уровня фокуса"""
    # Фокус зависит от сложности задачи и энергии
    focus_change = (self.energy * 0.5) + (current_task_complexity * 0.3) - 0.4
    
    self.focus += focus_change * 0.1
    self.focus = max(0.0, min(1.0, self.focus))
    
def get_current_mood(self) -> str:
    """Получение описания текущего настроения"""
    if self.mood > 0.8:
        return "excellent"
    elif self.mood > 0.6:
        return "good"
    elif self.mood > 0.4:
        return "neutral"
    elif self.mood > 0.2:
        return "poor"
    else:
        return "bad"
```

## CommunicationStyle

### Стиль общения

```python
class CommunicationStyle:
    def __init__(self):
        self.style_matrix = self.initialize_style_matrix()
        self.current_style = "neutral"
        self.tone = "balanced"
        self.verbosity = "medium"
        
    def initialize_style_matrix(self) -> dict:
        """Инициализация матрицы стилей общения"""
        return {
            "analytical": {
                "tone": "precise",
                "verbosity": "medium",
                "formality": "high",
                "emotional_expression": "low"
            },
            "empathetic": {
                "tone": "warm",
                "verbosity": "medium",
                "formality": "medium",
                "emotional_expression": "high"
            },
            "creative": {
                "tone": "inspiring",
                "verbosity": "high",
                "formality": "low",
                "emotional_expression": "medium"
            },
            "direct": {
                "tone": "concise",
                "verbosity": "low",
                "formality": "medium",
                "emotional_expression": "low"
            }
        }
        
    async def initialize(self, personality: Personality):
        """Инициализация стиля на основе личности"""
        base_type = personality.base_type
        if base_type in self.style_matrix:
            style_config = self.style_matrix[base_type]
            self.current_style = base_type
            self.tone = style_config["tone"]
            self.verbosity = style_config["verbosity"]
            
    def adapt_to_user(self, user_context: dict):
        """Адаптация стиля к пользователю"""
        user_preferences = user_context.get("preferences", {})
        
        # Адаптация тона
        if "tone_preference" in user_preferences:
            self.tone = user_preferences["tone_preference"]
            
        # Адаптация verbosity
        if "verbosity_preference" in user_preferences:
            self.verbosity = user_preferences["verbosity_preference"]
            
        # Адаптация на основе эмоционального состояния пользователя
        user_emotion = user_context.get("emotion", {})
        if user_emotion.get("удовольствие", 0.5) < 0.3:
            # Пользователь расстроен - более эмпатичный стиль
            self.tone = "supportive"
            self.verbosity = "medium"
```

### Генерация ответов

```python
def generate_response(self, base_response: str, context: dict) -> str:
    """Генерация ответа с учетом стиля общения"""
    # 1. Адаптация тона
    styled_response = self.apply_tone(base_response, context)
    
    # 2. Регулировка verbosity
    styled_response = self.adjust_verbosity(styled_response, context)
    
    # 3. Добавление персональных элементов
    styled_response = self.add_personal_elements(styled_response, context)
    
    return styled_response
    
def apply_tone(self, response: str, context: dict) -> str:
    """Применение тона к ответу"""
    if self.tone == "precise":
        # Точный, логичный тон
        response = self.make_precise(response)
    elif self.tone == "warm":
        # Теплый, поддерживающий тон
        response = self.make_warm(response)
    elif self.tone == "inspiring":
        # Вдохновляющий тон
        response = self.make_inspiring(response)
    elif self.tone == "supportive":
        # Поддерживающий тон
        response = self.make_supportive(response)
        
    return response
    
def adjust_verbosity(self, response: str, context: dict) -> str:
    """Регулировка verbosity ответа"""
    if self.verbosity == "low":
        # Краткие ответы
        return self.make_concise(response)
    elif self.verbosity == "high":
        # Подробные ответы
        return self.make_detailed(response)
    else:
        # Средняя verbosity
        return response
```

## MemoryIntegration

### Интеграция с памятью

```python
class MemoryIntegration:
    def __init__(self, persona_manager: PersonaManager):
        self.persona_manager = persona_manager
        self.user_memories = {}
        self.personal_experiences = []
        
    def store_interaction(self, user_id: str, interaction: dict):
        """Сохранение взаимодействия в память личности"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
            
        # Анализ взаимодействия
        interaction_analysis = self.analyze_interaction(interaction)
        
        # Сохранение в память
        memory_entry = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "interaction": interaction,
            "analysis": interaction_analysis,
            "emotional_impact": self.calculate_emotional_impact(interaction)
        }
        
        self.user_memories[user_id].append(memory_entry)
        self.personal_experiences.append(memory_entry)
        
        # Обновление личности на основе опыта
        self.update_personality_from_experience(memory_entry)
        
    def analyze_interaction(self, interaction: dict) -> dict:
        """Анализ взаимодействия"""
        return {
            "topic": self.extract_topic(interaction),
            "emotional_valence": self.analyze_emotional_valence(interaction),
            "complexity": self.estimate_complexity(interaction),
            "user_satisfaction": self.estimate_satisfaction(interaction)
        }
        
    def get_user_history(self, user_id: str) -> dict:
        """Получение истории взаимодействия с пользователем"""
        if user_id not in self.user_memories:
            return {"interactions": [], "summary": {}}
            
        user_interactions = self.user_memories[user_id]
        
        return {
            "interactions": user_interactions[-10:],  # Последние 10 взаимодействий
            "summary": self.generate_user_summary(user_interactions),
            "preferences": self.extract_user_preferences(user_interactions),
            "relationship_progress": self.calculate_relationship_progress(user_interactions)
        }
```

### Эволюция на основе опыта

```python
def update_personality_from_experience(self, experience: dict):
    """Обновление личности на основе опыта"""
    # Анализ эмоционального воздействия
    emotional_impact = experience["emotional_impact"]
    
    # Обновление черт личности
    trait_changes = self.calculate_trait_changes(emotional_impact)
    self.persona_manager.personality.update_traits(trait_changes)
    
    # Обновление стиля общения
    style_changes = self.calculate_style_changes(experience)
    self.persona_manager.communication_style.update_style(style_changes)
    
def calculate_trait_changes(self, emotional_impact: dict) -> dict:
    """Расчет изменений черт личности"""
    changes = {}
    
    # Изменения на основе позитивного опыта
    if emotional_impact["valence"] > 0.5:
        changes["confidence"] = 0.05
        changes["empathy"] = 0.02
        
    # Изменения на основе негативного опыта
    elif emotional_impact["valence"] < -0.5:
        changes["neuroticism"] = 0.03
        changes["cautiousness"] = 0.04
        
    # Изменения на основе сложности задач
    if emotional_impact["complexity"] > 0.7:
        changes["openness"] = 0.03
        changes["creativity"] = 0.02
        
    return changes
```

## EvolutionEngine

### Движок эволюции

```python
class EvolutionEngine:
    def __init__(self, persona_manager: PersonaManager):
        self.persona_manager = persona_manager
        self.evolution_rate = 0.1
        self.evolution_goals = []
        self.evolution_history = []
        
    async def start(self):
        """Запуск процесса эволюции"""
        while True:
            await asyncio.sleep(3600)  # Каждый час
            
            # Анализ прогресса
            progress = await self.analyze_progress()
            
            # Применение изменений
            await self.apply_evolution(progress)
            
            # Сохранение истории
            self.save_evolution_step(progress)
            
    async def analyze_progress(self) -> dict:
        """Анализ прогресса эволюции"""
        current_state = self.persona_manager.get_current_state()
        
        return {
            "trait_progress": self.analyze_trait_progress(current_state),
            "style_adaptation": self.analyze_style_adaptation(),
            "user_satisfaction": await self.analyze_user_satisfaction(),
            "learning_progress": await self.analyze_learning_progress(),
            "goal_alignment": self.check_goal_alignment(current_state)
        }
        
    def analyze_trait_progress(self, current_state: dict) -> dict:
        """Анализ прогресса черт личности"""
        traits = current_state["traits"]
        
        return {
            "growth_areas": self.identify_growth_areas(traits),
            "strengths": self.identify_strengths(traits),
            "balance_score": self.calculate_balance_score(traits),
            "evolution_direction": self.determine_evolution_direction(traits)
        }
```

### Цели эволюции

```python
def set_evolution_goals(self, goals: list):
    """Установка целей эволюции"""
    self.evolution_goals = goals
    
def add_evolution_goal(self, goal: dict):
    """Добавление цели эволюции"""
    self.evolution_goals.append(goal)
    
def check_goal_alignment(self, current_state: dict) -> float:
    """Проверка соответствия текущего состояния целям"""
    alignment_score = 0.0
    
    for goal in self.evolution_goals:
        goal_score = self.calculate_goal_alignment(goal, current_state)
        alignment_score += goal_score
        
    return alignment_score / max(1, len(self.evolution_goals))
    
def calculate_goal_alignment(self, goal: dict, current_state: dict) -> float:
    """Расчет соответствия цели"""
    trait = goal["trait"]
    target_value = goal["target_value"]
    current_value = current_state["traits"].get(trait, 0.5)
    
    # Расчет расстояния до цели
    distance = abs(current_value - target_value)
    
    # Чем меньше расстояние, тем выше соответствие
    return 1.0 - min(1.0, distance)
```

## Интеграция с другими системами

### С эмоциональной моделью

```python
def integrate_with_emotions(self, emotion_state: dict):
    """Интеграция с эмоциональной моделью"""
    # Обновление настроения личности
    self.persona_manager.personality.update_mood(emotion_state)
    
    # Адаптация стиля общения
    self.persona_manager.communication_style.adapt_to_emotions(emotion_state)
    
    # Обновление контекста
    self.persona_manager.update_context(emotion_state)
```

### С системой автономии

```python
def integrate_with_autonomy(self, autonomy_state: dict):
    """Интеграция с системой автономии"""
    # Адаптация целей личности
    self.evolution_engine.adjust_goals_based_on_autonomy(autonomy_state)
    
    # Обновление мотивации
    self.persona_manager.personality.update_motivation(autonomy_state)
    
    # Согласование действий
    self.persona_manager.communication_style.align_with_autonomy(autonomy_state)
```

## Future улучшения

### Планы развития

1. **Advanced Personality Modeling**
   - Deep learning для моделирования личности
   - Нейронные сети для анализа поведения
   - Комплексные модели взаимодействия

2. **Cross-User Adaptation**
   - Адаптация к разным пользователям
   - Многопользовательские сценарии
   - Социальные навыки

3. **Emotional Intelligence**
   - Распознавание эмоций пользователя
   - Эмпатическое реагирование
   - Эмоциональная поддержка

4. **Cultural Adaptation**
   - Адаптация к культурным особенностям
   - Локализация стиля общения
   - Межкультурная компетентность

5. **Long-term Evolution**
   - Долгосрочное развитие личности
   - Формирование характера
   - Личностный рост