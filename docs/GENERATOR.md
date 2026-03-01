# Generator Система

Этот документ описывает систему Generator в PAD+ AI.

## Обзор

Generator система обеспечивает:

- Генерацию ответов на основе контекста
- Интеграцию с несколькими LLM провайдерами
- Адаптацию стиля ответов
- Контроль качества генерации
- Оптимизацию производительности

## Архитектура Generator

### Компоненты

1. **ResponseGenerator** - Основной генератор ответов
2. **ProviderManager** - Менеджер провайдеров LLM
3. **ContextProcessor** - Процессор контекста
4. **QualityController** - Контроль качества
5. **StyleAdapter** - Адаптер стиля

### Процесс генерации

```
User Query → Context Processing → Provider Selection → Response Generation → Quality Control → Final Response
     ↓              ↓                    ↓                    ↓              ↓              ↓
  Context    →   Enhanced Context   →   Best Provider   →   Raw Response  →   Validation  →   Styled Response
     ↓              ↓                    ↓                    ↓              ↓              ↓
  RAG Data   →   Integrated Context →   Load Balancing  →   Post-processing →   Filtering  →   Delivery
```

## ResponseGenerator

### Основной генератор ответов

```python
class ResponseGenerator:
    def __init__(self):
        self.provider_manager = ProviderManager()
        self.context_processor = ContextProcessor()
        self.quality_controller = QualityController()
        self.style_adapter = StyleAdapter()
        self.generation_cache = {}
        self.generation_stats = GenerationStats()
        
    async def generate_response(self, prompt: str, context: dict, user_id: str = None) -> GenerationResult:
        """Генерация ответа"""
        # 1. Обработка контекста
        processed_context = await self.context_processor.process_context(prompt, context)
        
        # 2. Выбор провайдера
        provider = await self.provider_manager.select_provider(processed_context, user_id)
        
        # 3. Генерация ответа
        raw_response = await self.generate_with_provider(provider, prompt, processed_context)
        
        # 4. Контроль качества
        quality_result = await self.quality_controller.validate_response(raw_response, context)
        
        # 5. Адаптация стиля
        styled_response = await self.style_adapter.adapt_response(raw_response, context)
        
        # 6. Сохранение статистики
        await self.generation_stats.record_generation(provider, prompt, styled_response, quality_result)
        
        return GenerationResult(
            response=styled_response,
            provider=provider.name,
            quality_score=quality_result.score,
            processing_time=self.generation_stats.get_last_processing_time()
        )
        
    async def generate_with_provider(self, provider: BaseProvider, prompt: str, context: dict) -> str:
        """Генерация ответа через провайдера"""
        # Формирование промпта
        full_prompt = self.format_prompt(prompt, context)
        
        # Проверка кэша
        cache_key = self.generate_cache_key(provider.name, full_prompt)
        if cache_key in self.generation_cache:
            return self.generation_cache[cache_key]
            
        # Генерация через провайдера
        try:
            response = await provider.generate(full_prompt, **context.get("generation_params", {}))
            
            # Сохранение в кэш
            self.generation_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Provider {provider.name} failed: {e}")
            
            # Fallback к другому провайдеру
            fallback_provider = await self.provider_manager.get_fallback_provider(provider)
            if fallback_provider:
                return await self.generate_with_provider(fallback_provider, prompt, context)
            else:
                raise GenerationError(f"All providers failed for prompt: {prompt}")
```

### Форматирование промптов

```python
def format_prompt(self, user_prompt: str, context: dict) -> str:
    """Форматирование промпта для генерации"""
    # Шаблон промпта
    prompt_template = """
Ты - PAD+ AI, интеллектуальный ассистент с развитой эмоциональной моделью и автономией.

Контекст:
{context_summary}

История диалога:
{dialog_history}

Текущий запрос пользователя:
{user_prompt}

Требования к ответу:
1. Будь точным и информативным
2. Учитывай эмоциональное состояние пользователя
3. Поддерживай дружелюбный и профессиональный тон
4. Если не знаешь ответа - честно скажи об этом
5. Предлагай варианты дальнейшего взаимодействия

Ответ:"""
    
    # Сбор контекстной информации
    context_summary = self.build_context_summary(context)
    dialog_history = self.build_dialog_history(context)
    
    # Форматирование
    formatted_prompt = prompt_template.format(
        context_summary=context_summary,
        dialog_history=dialog_history,
        user_prompt=user_prompt
    )
    
    return formatted_prompt
    
def build_context_summary(self, context: dict) -> str:
    """Построение сводки контекста"""
    summary_parts = []
    
    # Эмоциональный контекст
    if "emotion" in context:
        emotion_state = context["emotion"]
        summary_parts.append(f"Эмоциональное состояние: {emotion_state}")
        
    # RAG контекст
    if "rag_context" in context and context["rag_context"]:
        rag_info = context["rag_context"][:3]  # Первые 3 результата
        rag_summary = "; ".join([f"{item['similarity']:.2f}: {item['user_message'][:50]}..." 
                               for item in rag_info])
        summary_parts.append(f"RAG контекст: {rag_summary}")
        
    # Цели и задачи
    if "goals" in context:
        goals = context["goals"]
        summary_parts.append(f"Текущие цели: {goals}")
        
    return "\n".join(summary_parts) if summary_parts else "Нет дополнительного контекста"
```

## ProviderManager

### Менеджер провайдеров

```python
class ProviderManager:
    def __init__(self):
        self.providers = {}
        self.provider_stats = {}
        self.load_balancer = LoadBalancer()
        self.fallback_chain = []
        
    async def add_provider(self, provider: BaseProvider):
        """Добавление провайдера"""
        self.providers[provider.name] = provider
        self.provider_stats[provider.name] = ProviderStats()
        
        # Обновление цепочки fallback
        self.update_fallback_chain()
        
    async def select_provider(self, context: dict, user_id: str = None) -> BaseProvider:
        """Выбор лучшего провайдера"""
        # 1. Фильтрация доступных провайдеров
        available_providers = await self.get_available_providers()
        
        if not available_providers:
            raise ProviderError("No available providers")
            
        # 2. Расчет приоритетов
        priorities = {}
        for provider in available_providers:
            priority = await self.calculate_provider_priority(provider, context, user_id)
            priorities[provider.name] = priority
            
        # 3. Выбор провайдера
        best_provider_name = max(priorities, key=priorities.get)
        best_provider = self.providers[best_provider_name]
        
        # 4. Обновление статистики
        self.provider_stats[best_provider_name].requests_count += 1
        
        return best_provider
        
    async def calculate_provider_priority(self, provider: BaseProvider, context: dict, user_id: str) -> float:
        """Расчет приоритета провайдера"""
        priority = 0.0
        
        # 1. Качество сервиса (историческая метрика)
        quality_score = self.provider_stats[provider.name].get_quality_score()
        priority += quality_score * 0.3
        
        # 2. Скорость ответа
        response_time = self.provider_stats[provider.name].get_avg_response_time()
        if response_time > 0:
            speed_score = 1.0 / (1.0 + response_time)  # Чем быстрее, тем выше
            priority += speed_score * 0.2
            
        # 3. Стоимость
        cost_score = provider.get_cost_score()
        priority += cost_score * 0.2
        
        # 4. Специализация
        specialization_score = await self.get_specialization_score(provider, context)
        priority += specialization_score * 0.2
        
        # 5. Нагрузка
        load_score = self.load_balancer.get_load_score(provider.name)
        priority += load_score * 0.1
        
        return priority
```

### Балансировка нагрузки

```python
class LoadBalancer:
    def __init__(self):
        self.provider_load = {}
        self.max_load_threshold = 0.8
        
    def get_load_score(self, provider_name: str) -> float:
        """Получение оценки нагрузки провайдера"""
        current_load = self.provider_load.get(provider_name, 0.0)
        
        # Чем меньше нагрузка, тем выше оценка
        load_score = 1.0 - min(current_load / self.max_load_threshold, 1.0)
        
        return load_score
        
    def update_load(self, provider_name: str, load_increase: float):
        """Обновление нагрузки провайдера"""
        current_load = self.provider_load.get(provider_name, 0.0)
        new_load = current_load + load_increase
        
        # Ограничение максимальной нагрузки
        self.provider_load[provider_name] = min(new_load, self.max_load_threshold * 2)
        
    def decrease_load(self, provider_name: str, time_passed: float):
        """Уменьшение нагрузки со временем"""
        if provider_name in self.provider_load:
            # Нагрузка уменьшается со временем
            decay_rate = 0.1  # Скорость уменьшения
            self.provider_load[provider_name] *= (1 - decay_rate * time_passed)
            self.provider_load[provider_name] = max(0.0, self.provider_load[provider_name])
```

## ContextProcessor

### Процессор контекста

```python
class ContextProcessor:
    def __init__(self):
        self.context_enhancers = []
        self.context_validators = []
        
    async def process_context(self, prompt: str, context: dict) -> dict:
        """Обработка и улучшение контекста"""
        # 1. Валидация контекста
        validated_context = await self.validate_context(context)
        
        # 2. Улучшение контекста
        enhanced_context = await self.enhance_context(validated_context, prompt)
        
        # 3. Оптимизация для генерации
        optimized_context = await self.optimize_context(enhanced_context)
        
        return optimized_context
        
    async def enhance_context(self, context: dict, prompt: str) -> dict:
        """Улучшение контекста"""
        enhanced_context = context.copy()
        
        # 1. Добавление RAG контекста
        if "rag_system" in context:
            rag_context = await context["rag_system"].search(prompt, n_results=3)
            enhanced_context["rag_context"] = rag_context
            
        # 2. Добавление информации о пользователе
        if "user_id" in context:
            user_info = await self.get_user_info(context["user_id"])
            enhanced_context["user_info"] = user_info
            
        # 3. Добавление эмоционального контекста
        if "emotion_manager" in context:
            emotion_state = context["emotion_manager"].get_state()
            enhanced_context["emotion_state"] = emotion_state
            
        # 4. Добавление целей и задач
        if "autonomy_manager" in context:
            goals = await context["autonomy_manager"].get_current_goals()
            enhanced_context["current_goals"] = goals
            
        return enhanced_context
        
    async def optimize_context(self, context: dict) -> dict:
        """Оптимизация контекста для генерации"""
        optimized_context = {}
        
        # 1. Ограничение размера контекста
        max_context_length = 4000  # Максимальная длина контекста в токенах
        
        # 2. Приоритизация информации
        priority_sections = [
            "user_prompt", "emotion_state", "rag_context", 
            "user_info", "current_goals", "dialog_history"
        ]
        
        current_length = 0
        for section in priority_sections:
            if section in context:
                section_content = context[section]
                section_length = self.estimate_token_length(section_content)
                
                if current_length + section_length <= max_context_length:
                    optimized_context[section] = section_content
                    current_length += section_length
                else:
                    # Обрезка секции
                    truncated_content = self.truncate_content(section_content, 
                                                            max_context_length - current_length)
                    optimized_context[section] = truncated_content
                    break
                    
        return optimized_context
```

## QualityController

### Контроль качества

```python
class QualityController:
    def __init__(self):
        self.quality_metrics = QualityMetrics()
        self.quality_thresholds = {
            "relevance": 0.7,
            "coherence": 0.8,
            "factuality": 0.8,
            "appropriateness": 0.9
        }
        
    async def validate_response(self, response: str, context: dict) -> QualityResult:
        """Валидация качества ответа"""
        # 1. Проверка релевантности
        relevance_score = await self.check_relevance(response, context)
        
        # 2. Проверка связности
        coherence_score = await self.check_coherence(response)
        
        # 3. Проверка фактичности
        factuality_score = await self.check_factuality(response, context)
        
        # 4. Проверка уместности
        appropriateness_score = await self.check_appropriateness(response, context)
        
        # 5. Расчет общего качества
        overall_quality = self.calculate_overall_quality({
            "relevance": relevance_score,
            "coherence": coherence_score,
            "factuality": factuality_score,
            "appropriateness": appropriateness_score
        })
        
        return QualityResult(
            score=overall_quality,
            metrics={
                "relevance": relevance_score,
                "coherence": coherence_score,
                "factuality": factuality_score,
                "appropriateness": appropriateness_score
            },
            is_valid=self.is_quality_acceptable(overall_quality)
        )
        
    async def check_relevance(self, response: str, context: dict) -> float:
        """Проверка релевантности ответа"""
        user_prompt = context.get("user_prompt", "")
        
        # Использование semantic similarity
        similarity = await self.calculate_semantic_similarity(user_prompt, response)
        
        # Проверка наличия ключевых слов из запроса
        keyword_coverage = self.check_keyword_coverage(user_prompt, response)
        
        # Комбинированная оценка
        relevance_score = (similarity * 0.7) + (keyword_coverage * 0.3)
        
        return relevance_score
```

### Проверка связности

```python
async def check_coherence(self, response: str) -> float:
    """Проверка связности ответа"""
    sentences = sent_tokenize(response)
    
    if len(sentences) < 2:
        return 1.0  # Очень короткие ответы считаются связными
        
    coherence_score = 0.0
    total_connections = 0
    
    # Проверка связности между соседними предложениями
    for i in range(len(sentences) - 1):
        sentence1 = sentences[i]
        sentence2 = sentences[i + 1]
        
        connection_score = await self.calculate_sentence_connection(sentence1, sentence2)
        coherence_score += connection_score
        total_connections += 1
        
    if total_connections > 0:
        coherence_score /= total_connections
        
    return coherence_score
    
async def calculate_sentence_connection(self, sentence1: str, sentence2: str) -> float:
    """Расчет связи между предложениями"""
    # Проверка логических связок
    logical_connectors = ["поэтому", "потому что", "следовательно", "однако", "но", "и", "а"]
    has_connector = any(connector in sentence2.lower() for connector in logical_connectors)
    
    # Проверка семантической близости
    semantic_similarity = await self.calculate_semantic_similarity(sentence1, sentence2)
    
    # Комбинированная оценка
    connection_score = (semantic_similarity * 0.7) + (1.0 if has_connector else 0.0) * 0.3
    
    return connection_score
```

## StyleAdapter

### Адаптер стиля

```python
class StyleAdapter:
    def __init__(self):
        self.style_templates = self.load_style_templates()
        self.emotion_style_mapping = self.load_emotion_style_mapping()
        
    async def adapt_response(self, response: str, context: dict) -> str:
        """Адаптация стиля ответа"""
        # 1. Определение целевого стиля
        target_style = await self.determine_target_style(context)
        
        # 2. Применение стилистических преобразований
        styled_response = await self.apply_style_transformations(response, target_style)
        
        # 3. Добавление эмоциональных маркеров
        final_response = await self.add_emotional_markers(styled_response, context)
        
        return final_response
        
    async def determine_target_style(self, context: dict) -> dict:
        """Определение целевого стиля"""
        style = {
            "tone": "neutral",
            "verbosity": "medium",
            "formality": "medium",
            "emotional_coloring": "minimal"
        }
        
        # Адаптация по эмоциональному состоянию пользователя
        if "emotion_state" in context:
            user_emotion = context["emotion_state"]
            style = self.adapt_style_to_emotion(style, user_emotion)
            
        # Адаптация по типу запроса
        if "intent" in context:
            intent_type = context["intent"]
            style = self.adapt_style_to_intent(style, intent_type)
            
        # Адаптация по предпочтениям пользователя
        if "user_preferences" in context:
            user_prefs = context["user_preferences"]
            style = self.adapt_style_to_preferences(style, user_prefs)
            
        return style
        
    def adapt_style_to_emotion(self, style: dict, emotion_state: dict) -> dict:
        """Адаптация стиля под эмоциональное состояние"""
        pleasure = emotion_state.get("удовольствие", 0.5)
        arousal = emotion_state.get("возбуждение", 0.5)
        
        # Адаптация тона
        if pleasure > 0.8:
            style["tone"] = "enthusiastic"
        elif pleasure < 0.3:
            style["tone"] = "supportive"
            
        # Адаптация verbosity
        if arousal > 0.8:
            style["verbosity"] = "high"
        elif arousal < 0.3:
            style["verbosity"] = "low"
            
        return style
```

### Стилистические преобразования

```python
async def apply_style_transformations(self, response: str, style: dict) -> str:
    """Применение стилистических преобразований"""
    styled_response = response
    
    # 1. Преобразование тона
    if style["tone"] == "enthusiastic":
        styled_response = self.make_enthusiastic(styled_response)
    elif style["tone"] == "supportive":
        styled_response = self.make_supportive(styled_response)
    elif style["tone"] == "professional":
        styled_response = self.make_professional(styled_response)
        
    # 2. Регулировка verbosity
    if style["verbosity"] == "high":
        styled_response = self.make_detailed(styled_response)
    elif style["verbosity"] == "low":
        styled_response = self.make_concise(styled_response)
        
    # 3. Регулировка формальности
    if style["formality"] == "high":
        styled_response = self.make_formal(styled_response)
    elif style["formality"] == "low":
        styled_response = self.make_informal(styled_response)
        
    return styled_response
    
def make_enthusiastic(self, response: str) -> str:
    """Сделать ответ более энтузиастичным"""
    # Добавление позитивных частиц
    if not response.startswith(("Отлично", "Замечательно", "Прекрасно")):
        response = "Отличный вопрос! " + response
        
    # Добавление восклицательных знаков (умеренно)
    if response.count("!") < 2 and "?" not in response[-10:]:
        response += "!"
        
    return response
```

## Future улучшения

### Планы развития

1. **Advanced Response Generation**
   - Multi-turn dialogue optimization
   - Context-aware generation
   - Personalized response styles

2. **Provider Intelligence**
   - Dynamic provider selection
   - Real-time performance monitoring
   - Automatic failover mechanisms

3. **Quality Enhancement**
   - Advanced factuality checking
   - Real-time quality monitoring
   - Adaptive quality thresholds

4. **Performance Optimization**
   - Response caching strategies
   - Parallel generation
   - Memory optimization

5. **Style Evolution**
   - Adaptive style learning
   - User preference evolution
   - Cross-cultural style adaptation