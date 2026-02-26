# Intent Router Система

Этот документ описывает систему Intent Router в PAD+ AI.

## Обзор

Intent Router система обеспечивает:

- Классификацию намерений пользователя
- Маршрутизацию запросов к соответствующим модулям
- Адаптивное распознавание интентов
- Обучение на основе опыта
- Многомерный анализ запросов

## Архитектура Intent Router

### Компоненты

1. **IntentClassifier** - Классификатор интентов
2. **IntentRouter** - Маршрутизатор запросов
3. **IntentMemory** - Память интентов
4. **IntentLearning** - Система обучения
5. **IntentAnalytics** - Аналитика интентов

### Типы интентов

```python
INTENT_TYPES = {
    # Информационные запросы
    "information_request": {
        "description": "Запрос информации",
        "keywords": ["что", "как", "почему", "где", "когда"],
        "subtypes": ["definition", "explanation", "fact", "procedure"]
    },
    
    # Задачи и действия
    "task_execution": {
        "description": "Выполнение задачи",
        "keywords": ["сделай", "выполни", "реши", "найди", "создай"],
        "subtypes": ["calculation", "search", "generation", "analysis"]
    },
    
    # Общение и социальное
    "social_interaction": {
        "description": "Социальное взаимодействие",
        "keywords": ["привет", "пока", "спасибо", "извини"],
        "subtypes": ["greeting", "farewell", "gratitude", "apology"]
    },
    
    # Эмоциональная поддержка
    "emotional_support": {
        "description": "Эмоциональная поддержка",
        "keywords": ["грустно", "рад", "злюсь", "боюсь"],
        "subtypes": ["comfort", "encouragement", "advice", "listening"]
    },
    
    # Обучение и развитие
    "learning_request": {
        "description": "Запрос на обучение",
        "keywords": ["объясни", "научи", "расскажи", "покажи"],
        "subtypes": ["tutorial", "example", "practice", "feedback"]
    }
}
```

## IntentClassifier

### Классификатор интентов

```python
class IntentClassifier:
    def __init__(self):
        self.intent_models = {}
        self.feature_extractors = {}
        self.confidence_threshold = 0.7
        self.fallback_threshold = 0.3
        
    def initialize_models(self):
        """Инициализация моделей классификации"""
        # Загрузка предобученных моделей
        self.intent_models = {
            "text_classifier": self.load_text_classifier(),
            "keyword_matcher": self.load_keyword_matcher(),
            "context_analyzer": self.load_context_analyzer(),
            "sentiment_analyzer": self.load_sentiment_analyzer()
        }
        
        # Инициализация feature extractors
        self.feature_extractors = {
            "ngrams": NGramExtractor(),
            "entities": EntityExtractor(),
            "sentiment": SentimentExtractor(),
            "keywords": KeywordExtractor()
        }
        
    def classify_intent(self, text: str, context: dict = None) -> IntentResult:
        """Классификация интента"""
        # 1. Извлечение признаков
        features = self.extract_features(text, context)
        
        # 2. Классификация
        predictions = self.make_predictions(features)
        
        # 3. Агрегация результатов
        aggregated_result = self.aggregate_predictions(predictions)
        
        # 4. Проверка уверенности
        if aggregated_result.confidence < self.fallback_threshold:
            # Fallback классификация
            aggregated_result = self.fallback_classification(text, context)
            
        return aggregated_result
        
    def extract_features(self, text: str, context: dict) -> dict:
        """Извлечение признаков для классификации"""
        features = {}
        
        # Текстовые признаки
        features["text_features"] = self.feature_extractors["ngrams"].extract(text)
        
        # Сущности
        features["entities"] = self.feature_extractors["entities"].extract(text)
        
        # Сентимент
        features["sentiment"] = self.feature_extractors["sentiment"].extract(text)
        
        # Ключевые слова
        features["keywords"] = self.feature_extractors["keywords"].extract(text)
        
        # Контекстные признаки
        if context:
            features["context_features"] = self.extract_context_features(context)
            
        return features
```

### Многомодельная классификация

```python
def make_predictions(self, features: dict) -> dict:
    """Получение предсказаний от всех моделей"""
    predictions = {}
    
    # Text classifier prediction
    if "text_classifier" in self.intent_models:
        text_features = features.get("text_features", [])
        predictions["text_classifier"] = self.intent_models["text_classifier"].predict(text_features)
        
    # Keyword matcher prediction
    if "keyword_matcher" in self.intent_models:
        keywords = features.get("keywords", [])
        predictions["keyword_matcher"] = self.intent_models["keyword_matcher"].predict(keywords)
        
    # Context analyzer prediction
    if "context_analyzer" in self.intent_models:
        context_features = features.get("context_features", {})
        predictions["context_analyzer"] = self.intent_models["context_analyzer"].predict(context_features)
        
    # Sentiment analyzer prediction
    if "sentiment_analyzer" in self.intent_models:
        sentiment = features.get("sentiment", {})
        predictions["sentiment_analyzer"] = self.intent_models["sentiment_analyzer"].predict(sentiment)
        
    return predictions
    
def aggregate_predictions(self, predictions: dict) -> IntentResult:
    """Агрегация предсказаний от всех моделей"""
    # Веса моделей
    weights = {
        "text_classifier": 0.4,
        "keyword_matcher": 0.3,
        "context_analyzer": 0.2,
        "sentiment_analyzer": 0.1
    }
    
    # Сбор всех предсказанных интентов
    intent_scores = defaultdict(float)
    
    for model_name, prediction in predictions.items():
        if model_name in weights:
            weight = weights[model_name]
            for intent, score in prediction.items():
                intent_scores[intent] += score * weight
                
    # Нормализация scores
    total_score = sum(intent_scores.values())
    if total_score > 0:
        for intent in intent_scores:
            intent_scores[intent] /= total_score
            
    # Выбор лучшего интента
    best_intent = max(intent_scores, key=intent_scores.get)
    confidence = intent_scores[best_intent]
    
    return IntentResult(
        intent=best_intent,
        confidence=confidence,
        scores=dict(intent_scores),
        predictions=predictions
    )
```

## IntentRouter

### Маршрутизатор запросов

```python
class IntentRouter:
    def __init__(self, intent_classifier: IntentClassifier):
        self.intent_classifier = intent_classifier
        self.route_map = self.initialize_route_map()
        self.fallback_handler = FallbackHandler()
        
    def initialize_route_map(self) -> dict:
        """Инициализация карты маршрутизации"""
        return {
            "information_request": {
                "handler": "information_handler",
                "priority": 1,
                "subtypes": {
                    "definition": "definition_handler",
                    "explanation": "explanation_handler",
                    "fact": "fact_handler",
                    "procedure": "procedure_handler"
                }
            },
            "task_execution": {
                "handler": "task_handler",
                "priority": 2,
                "subtypes": {
                    "calculation": "calculation_handler",
                    "search": "search_handler",
                    "generation": "generation_handler",
                    "analysis": "analysis_handler"
                }
            },
            "social_interaction": {
                "handler": "social_handler",
                "priority": 3,
                "subtypes": {
                    "greeting": "greeting_handler",
                    "farewell": "farewell_handler",
                    "gratitude": "gratitude_handler",
                    "apology": "apology_handler"
                }
            },
            "emotional_support": {
                "handler": "emotional_handler",
                "priority": 4,
                "subtypes": {
                    "comfort": "comfort_handler",
                    "encouragement": "encouragement_handler",
                    "advice": "advice_handler",
                    "listening": "listening_handler"
                }
            },
            "learning_request": {
                "handler": "learning_handler",
                "priority": 5,
                "subtypes": {
                    "tutorial": "tutorial_handler",
                    "example": "example_handler",
                    "practice": "practice_handler",
                    "feedback": "feedback_handler"
                }
            }
        }
        
    async def route_request(self, text: str, context: dict = None) -> RouteResult:
        """Маршрутизация запроса"""
        # 1. Классификация интента
        intent_result = self.intent_classifier.classify_intent(text, context)
        
        # 2. Определение маршрута
        route = self.determine_route(intent_result, context)
        
        # 3. Проверка доступности обработчика
        if not self.is_handler_available(route.handler):
            route = self.find_alternative_route(intent_result, context)
            
        # 4. Создание результата маршрутизации
        route_result = RouteResult(
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            handler=route.handler,
            priority=route.priority,
            context=context,
            metadata={
                "classification_details": intent_result,
                "route_details": route
            }
        )
        
        # 5. Логирование маршрутизации
        await self.log_routing(route_result)
        
        return route_result
```

### Альтернативная маршрутизация

```python
def find_alternative_route(self, intent_result: IntentResult, context: dict) -> Route:
    """Поиск альтернативного маршрута"""
    # 1. Поиск по схожим интентам
    similar_intents = self.find_similar_intents(intent_result.intent)
    
    for similar_intent in similar_intents:
        route = self.get_route_for_intent(similar_intent)
        if self.is_handler_available(route.handler):
            return route
            
    # 2. Поиск по ключевым словам
    keywords = self.extract_keywords_from_text(context.get("text", ""))
    keyword_route = self.find_route_by_keywords(keywords)
    if keyword_route and self.is_handler_available(keyword_route.handler):
        return keyword_route
        
    # 3. Fallback маршрут
    return self.fallback_handler.get_fallback_route(intent_result)
    
def find_similar_intents(self, intent: str) -> list:
    """Поиск схожих интентов"""
    # Использование семантической близости
    intent_embeddings = self.get_intent_embeddings()
    current_embedding = intent_embeddings.get(intent, [])
    
    similarities = {}
    for other_intent, other_embedding in intent_embeddings.items():
        if other_intent != intent:
            similarity = self.calculate_similarity(current_embedding, other_embedding)
            similarities[other_intent] = similarity
            
    # Сортировка по схожести
    sorted_similar = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
    
    return [intent for intent, score in sorted_similar if score > 0.5]
```

## IntentMemory

### Память интентов

```python
class IntentMemory:
    def __init__(self):
        self.intent_history = []
        self.intent_patterns = {}
        self.user_intent_preferences = {}
        
    def store_intent_interaction(self, user_id: str, text: str, intent: str, confidence: float, result: dict):
        """Сохранение взаимодействия с интентом"""
        interaction = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "text": text,
            "intent": intent,
            "confidence": confidence,
            "result": result,
            "features": self.extract_features(text)
        }
        
        self.intent_history.append(interaction)
        
        # Обновление паттернов
        self.update_intent_patterns(interaction)
        
        # Обновление предпочтений пользователя
        self.update_user_preferences(user_id, intent, confidence)
        
    def extract_features(self, text: str) -> dict:
        """Извлечение признаков из текста"""
        return {
            "keywords": self.extract_keywords(text),
            "entities": self.extract_entities(text),
            "sentiment": self.analyze_sentiment(text),
            "length": len(text),
            "complexity": self.calculate_complexity(text)
        }
        
    def update_intent_patterns(self, interaction: dict):
        """Обновление паттернов интентов"""
        intent = interaction["intent"]
        
        if intent not in self.intent_patterns:
            self.intent_patterns[intent] = {
                "examples": [],
                "keywords": defaultdict(int),
                "entities": defaultdict(int),
                "sentiment_distribution": defaultdict(int),
                "time_patterns": defaultdict(int)
            }
            
        pattern = self.intent_patterns[intent]
        
        # Добавление примера
        pattern["examples"].append(interaction["text"])
        
        # Обновление статистики
        features = interaction["features"]
        for keyword in features["keywords"]:
            pattern["keywords"][keyword] += 1
            
        for entity in features["entities"]:
            pattern["entities"][entity] += 1
            
        sentiment = features["sentiment"]
        pattern["sentiment_distribution"][sentiment] += 1
        
        hour = interaction["timestamp"].hour
        pattern["time_patterns"][hour] += 1
        
        # Ограничение размера примеров
        if len(pattern["examples"]) > 100:
            pattern["examples"].pop(0)
```

### Анализ предпочтений пользователей

```python
def update_user_preferences(self, user_id: str, intent: str, confidence: float):
    """Обновление предпочтений пользователя"""
    if user_id not in self.user_intent_preferences:
        self.user_intent_preferences[user_id] = {
            "intent_frequencies": defaultdict(int),
            "confidence_scores": defaultdict(list),
            "preferred_handlers": defaultdict(int),
            "time_preferences": defaultdict(int)
        }
        
    user_prefs = self.user_intent_preferences[user_id]
    
    # Обновление частоты
    user_prefs["intent_frequencies"][intent] += 1
    
    # Обновление confidence scores
    user_prefs["confidence_scores"][intent].append(confidence)
    
    # Ограничение истории confidence
    if len(user_prefs["confidence_scores"][intent]) > 50:
        user_prefs["confidence_scores"][intent].pop(0)
        
    # Обновление временных предпочтений
    hour = datetime.now().hour
    user_prefs["time_preferences"][hour] += 1
```

## IntentLearning

### Система обучения

```python
class IntentLearning:
    def __init__(self, intent_classifier: IntentClassifier, intent_memory: IntentMemory):
        self.intent_classifier = intent_classifier
        self.intent_memory = intent_memory
        self.learning_rate = 0.1
        self.min_samples_for_learning = 10
        
    async def learn_from_interactions(self):
        """Обучение на основе взаимодействий"""
        # 1. Анализ истории взаимодействий
        recent_interactions = self.intent_memory.intent_history[-100:]
        
        # 2. Поиск паттернов ошибок
        error_patterns = self.analyze_error_patterns(recent_interactions)
        
        # 3. Обновление моделей
        if error_patterns:
            await self.update_classifier_models(error_patterns)
            
        # 4. Обновление feature extractors
        await self.update_feature_extractors()
        
    def analyze_error_patterns(self, interactions: list) -> dict:
        """Анализ паттернов ошибок"""
        error_patterns = {
            "low_confidence": [],
            "misclassified": [],
            "context_issues": []
        }
        
        for interaction in interactions:
            confidence = interaction["confidence"]
            intent = interaction["intent"]
            
            # Низкая уверенность
            if confidence < 0.5:
                error_patterns["low_confidence"].append(interaction)
                
            # Возможная ошибка классификации
            if self.is_potential_misclassification(interaction):
                error_patterns["misclassified"].append(interaction)
                
            # Проблемы с контекстом
            if self.has_context_issues(interaction):
                error_patterns["context_issues"].append(interaction)
                
        return error_patterns
        
    def is_potential_misclassification(self, interaction: dict) -> bool:
        """Проверка на возможную ошибку классификации"""
        text = interaction["text"]
        predicted_intent = interaction["intent"]
        
        # Проверка по ключевым словам
        keywords = self.extract_keywords(text)
        for keyword in keywords:
            likely_intents = self.get_intents_for_keyword(keyword)
            if predicted_intent not in likely_intents:
                return True
                
        return False
```

### Обновление моделей

```python
async def update_classifier_models(self, error_patterns: dict):
    """Обновление моделей классификатора"""
    # 1. Обновление text classifier
    if error_patterns["misclassified"]:
        await self.update_text_classifier(error_patterns["misclassified"])
        
    # 2. Обновление keyword matcher
    if error_patterns["low_confidence"]:
        await self.update_keyword_matcher(error_patterns["low_confidence"])
        
    # 3. Обновление context analyzer
    if error_patterns["context_issues"]:
        await self.update_context_analyzer(error_patterns["context_issues"])
        
    # 4. Перекалибровка confidence thresholds
    await self.recalibrate_confidence_thresholds()
    
async def update_text_classifier(self, misclassified_interactions: list):
    """Обновление текстового классификатора"""
    # Подготовка training data
    training_data = []
    for interaction in misclassified_interactions:
        text = interaction["text"]
        correct_intent = self.get_correct_intent(text)  # Требуется human feedback
        if correct_intent:
            training_data.append((text, correct_intent))
            
    if training_data:
        # Обучение модели
        await self.intent_classifier.retrain_text_classifier(training_data)
        
async def recalibrate_confidence_thresholds(self):
    """Перекалибровка порогов уверенности"""
    # Анализ текущих результатов
    recent_results = self.intent_memory.intent_history[-50:]
    
    # Расчет оптимальных порогов
    optimal_thresholds = self.calculate_optimal_thresholds(recent_results)
    
    # Обновление порогов
    self.intent_classifier.confidence_threshold = optimal_thresholds["confidence"]
    self.intent_classifier.fallback_threshold = optimal_thresholds["fallback"]
```

## Future улучшения

### Планы развития

1. **Advanced Intent Recognition**
   - Deep learning для распознавания интентов
   - Мультимодальное распознавание
   - Контекстно-зависимые интенты

2. **Intent Prediction**
   - Прогнозирование намерений пользователя
   - Предиктивная маршрутизация
   - Proactive intent handling

3. **Cross-user Intent Learning**
   - Обучение на основе опыта других пользователей
   - Transfer learning между пользователями
   - Коллективное обучение

4. **Intent Evolution Tracking**
   - Отслеживание эволюции интентов
   - Адаптация к изменяющимся потребностям
   - Долгосрочное обучение

5. **Intent-based Personalization**
   - Персонализация на основе интентов
   - Индивидуальные маршруты
   - Адаптивные обработчики