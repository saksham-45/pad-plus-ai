# 🧠 X-Ray Brain — План реализации

## Обзор

**Цель:** Превратить X-Ray из системы наблюдения (logger) в **центр принятия решений (Brain)** системы PAD+ AI.

**Текущее состояние:** X-Ray Level 3 — это Cognitive Infrastructure с трассировкой, метриками и аналитикой, но **без полномочий принятия решений**.

**Целевое состояние:** X-Ray Brain — Decision Engine + Meta-Learning + State Control, который принимает ВСЕ стратегические решения, а Pipeline становится просто исполнителем.

---

## 📊 АНАЛИЗ ТЕКУЩЕЙ АРХИТЕКТУРЫ

### Существующие компоненты (которые можно использовать)

| Компонент | Файл | Текущая роль | Потенциал для Brain |
|-----------|------|--------------|---------------------|
| `CognitiveState` | `xray/cognitive_state.py` | Отслеживание метрик | ✅ Основа для Decision State |
| `MetaCognitiveController` | `meta_controller.py` | Принятие стратегий | ⚠️ Частично дублирует, нужно объединить |
| `CognitiveBudget` | `agi/budget.py` | Оценка сложности | ✅ Интегрировать в Brain |
| `ModelRouter` | `agi/model_router.py` | Выбор модели | ✅ Интегрировать в Brain |
| `TruthLoop` | `truth_loop.py` | Верификация | ✅ Использовать для Reflection |
| `PipelineExecutor` | `pipeline.py` | Оркестрация | ❌ Должен стать исполнителем |

### Проблемы текущей архитектуры

1. **Распределённая логика решений:**
   - `meta_controller.py` — выбирает стратегию
   - `agi/budget.py` — определяет режим мышления
   - `agi/model_router.py` — выбирает модель
   - `pipeline.py` — содержит if/else логику
   - `cognitive_state.py` — только отслеживает, не решает

2. **Отсутствие Meta-Learning:**
   - Нет статистики успешности стратегий
   - Нет адаптации на основе истории
   - Нет замкнутого цикла обучения

3. **Отсутствие Reflection Loop:**
   - TruthLoop проверяет факты, но не решения
   - Нет анализа "почему стратегия сработала/не сработала"

---

## 🏗️ ЦЕЛЕВАЯ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────────────┐
│                        X-Ray Brain                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Decision Engine                           ││
│  │  • Strategy Selector (какую стратегию выбрать)              ││
│  │  • Model Router (какой LLM вызвать)                         ││
│  │  • Memory Decider (использовать ли память)                  ││
│  │  • Depth Estimator (уровень глубины анализа)                ││
│  │  • Verification Decider (нужен ли TruthLoop)                ││
│  │  • Tone Selector (какой тон применить)                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Meta-Learner                              ││
│  │  • Strategy Statistics (успех/неудачи по стратегиям)         ││
│  │  • Performance Tracking (время, уверенность, качество)      ││
│  │  • Adaptive Weights (адаптивные веса решений)               ││
│  │  • Pattern Recognition (распознавание паттернов)            ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    System State                              ││
│  │  • Cognitive Load (текущая нагрузка)                        ││
│  │  • Confidence Level (уровень уверенности)                   ││
│  │  • Resource Availability (доступность ресурсов)             ││
│  │  • Recent Performance (последние результаты)                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Reflection Loop                           ││
│  │  • Post-Decision Analysis (анализ после выполнения)         ││
│  │  • Outcome Evaluation (оценка результата)                   ││
│  │  • Strategy Adjustment (корректировка стратегий)            ││
│  │  • Learning Update (обновление мета-обучения)               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Pipeline (Executor)                       │
│  • Только выполняет полученные инструкции                        │
│  • Не принимает стратегических решений                          │
│  • Возвращает результат + метрики для Reflection               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 ПЛАН РЕАЛИЗАЦИИ ПО ЭТАПАМ

### 🔥 ЭТАП 1: Создание XRayBrain (Decision Engine)

**Файл:** `backend/core/xray/brain.py`

```python
class XRayBrain:
    """
    🧠 X-Ray Brain — центр принятия решений
    
    Принимает ВСЕ стратегические решения:
    - Какую стратегию выбрать
    - Какой LLM использовать
    - Использовать ли память
    - Какой уровень глубины
    - Нужен ли TruthLoop
    - Какой тон применить
    """
    
    def decide(self, input_text: str, context: dict) -> Decision:
        """Главный метод принятия решений"""
        pass
    
    def _choose_strategy(self, text: str, state: SystemState) -> str:
        """Выбор стратегии обработки"""
        pass
    
    def _select_model(self, decision: Decision) -> str:
        """Выбор LLM модели"""
        pass
    
    def _should_use_memory(self, text: str) -> bool:
        """Решение об использовании памяти"""
        pass
    
    def _estimate_depth(self, text: str) -> int:
        """Оценка необходимой глубины анализа"""
        pass
```

**Подзадачи:**
1.1. Создать `backend/core/xray/brain.py` с базовой структурой
1.2. Реализовать `_choose_strategy()` — анализ текста + эвристики
1.3. Реализовать `_select_model()` — интеграция с ModelRouter
1.4. Реализовать `_should_use_memory()` — решение об использовании RAG/facts
1.5. Реализовать `_estimate_depth()` — оценка сложности запроса
1.6. Создать класс `Decision` с полями: strategy, model, use_memory, depth, tone, use_verification

**Критерий готовности:**
- Pipeline запрашивает решение у XRayBrain перед выполнением
- Все решения принимаются в одном месте

---

### 🔥 ЭТАП 2: System State (Состояние системы)

**Файл:** `backend/core/xray/system_state.py` (новый)

```python
class SystemState:
    """
    Текущее состояние системы
    
    Отслеживает:
    - Когнитивную нагрузку
    - Доступность ресурсов
    - Recent performance
    - Активные сессии
    """
    
    load: float           # 0.0 - 1.0
    confidence: float     # 0.0 - 1.0
    available_resources: Dict[str, bool]
    recent_errors: int
    active_sessions: int
```

**Подзадачи:**
2.1. Создать `backend/core/xray/system_state.py`
2.2. Реализовать отслеживание когнитивной нагрузки
2.3. Реализовать мониторинг доступности ресурсов (RAG, LLM, память)
2.4. Реализовать подсчёт recent errors
2.5. Интегрировать с CognitiveState (существующий)

**Критерий готовности:**
- SystemState обновляется в реальном времени
- Brain использует state для принятия решений

---

### 🔥 ЭТАП 3: Meta-Learner (Самообучение)

**Файл:** `backend/core/xray/meta_learner.py` (новый)

```python
class MetaLearner:
    """
    Система мета-обучения
    
    Анализирует:
    - Какие стратегии работают лучше
    - Какие модели дают лучшие результаты
    - Паттерны успешных/неуспешных запросов
    
    Адаптирует:
    - Веса стратегий
    - Приоритеты моделей
    - Пороги решений
    """
    
    def record_outcome(self, decision: Decision, result: PipelineResult):
        """Записывает результат выполнения"""
        pass
    
    def get_strategy_stats(self, strategy: str) -> StrategyStats:
        """Возвращает статистику по стратегии"""
        pass
    
    def should_adjust_strategy(self, current_strategy: str) -> Optional[str]:
        """Рекомендует смену стратегии на основе истории"""
        pass
```

**Подзадачи:**
3.1. Создать `backend/core/xray/meta_learner.py`
3.2. Реализовать `record_outcome()` — запись результатов
3.3. Реализовать статистику по стратегиям (success/fail/avg_confidence)
3.4. Реализовать `get_strategy_stats()` — получение статистики
3.5. Реализовать `should_adjust_strategy()` — рекомендации по смене стратегии
3.6. Сохранение статистики в файл/БД

**Критерий готовности:**
- Система запоминает результаты каждого запроса
- Статистика влияет на будущие решения

---

### 🔥 ЭТАП 4: Reflection Loop (Рефлексия)

**Файл:** `backend/core/xray/reflection.py` (новый)

```python
class ReflectionLoop:
    """
    Контур рефлексии
    
    После каждого ответа:
    1. Анализирует результат
    2. Сравнивает с ожидаемым
    3. Обновляет мета-обучение
    4. Корректирует будущие решения
    """
    
    def reflect(self, decision: Decision, result: PipelineResult) -> ReflectionResult:
        """Анализирует результат и обновляет систему"""
        pass
    
    def _analyze_confidence_gap(self, expected: float, actual: float) -> float:
        """Анализирует разрыв между ожидаемой и фактической уверенностью"""
        pass
    
    def _detect_pattern(self, text: str, result: PipelineResult) -> Optional[str]:
        """Обнаруживает паттерны в запросах"""
        pass
```

**Подзадачи:**
4.1. Создать `backend/core/xray/reflection.py`
4.2. Реализовать `reflect()` — главный метод рефлексии
4.3. Интегрировать с TruthLoop для верификации
4.4. Интегрировать с MetaLearner для обновления статистики
4.5. Реализовать обнаружение паттернов (повторяющиеся проблемы)

**Критерий готовности:**
- После каждого ответа система анализирует результат
- Мета-обучение обновляется на основе рефлексии

---

### 🔥 ЭТАП 5: Pipeline Refactor (Перенос логики)

**Изменения в `backend/core/pipeline.py`:**

**Подзадачи:**
5.1. Удалить вызовы `meta_controller.decide_strategy()` из pipeline
5.2. Удалить вызовы `cognitive_budget.allocate()` из pipeline
5.3. Удалить вызовы `model_router.select()` из pipeline
5.4. Добавить вызов `xray_brain.decide()` в начале execute()
5.5. Использовать решение Brain для всей обработки
5.6. Добавить вызов `reflection_loop.reflect()` после выполнения
5.7. Упростить pipeline до чистого исполнителя

**До (упрощённо):**
```python
async def execute(self, user_message, context):
    # Pipeline сам принимает решения
    strategy = meta.decide_strategy(user_message)
    model = router.select(strategy)
    # ... выполнение ...
```

**После:**
```python
async def execute(self, user_message, context):
    # Brain принимает решения
    decision = xray_brain.decide(user_message, context)
    # ... выполнение по инструкции Brain ...
    # Reflection анализирует результат
    reflection.reflect(decision, result)
```

**Критерий готовности:**
- Pipeline не содержит if/else для выбора стратегии
- Все решения приходят из X-Ray Brain

---

### 🔥 ЭТАП 6: Интеграция существующих компонентов

**Подзадачи:**
6.1. Интегрировать CognitiveState в SystemState
6.2. Использовать TruthLoop в Reflection
6.3. Интегрировать ResponseGuard как часть исполнения
6.4. Использовать существующие memory компоненты по решению Brain

**Критерий готовности:**
- Все существующие компоненты работают под управлением Brain

---

### 🔥 ЭТАП 7: API и маршруты

**Новые endpoints в `backend/api/xray_routes.py`:**

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/xray/brain/status` | GET | Текущее состояние Brain |
| `/api/v1/xray/brain/stats` | GET | Статистика решений |
| `/api/v1/xray/meta/strategies` | GET | Статистика по стратегиям |
| `/api/v1/xray/meta/adjust` | POST | Ручная корректировка весов |
| `/api/v1/xray/reflection/recent` | GET | Последние рефлексии |

**Подзадачи:**
7.1. Добавить endpoints для Brain status
7.2. Добавить endpoints для Meta-Learner stats
7.3. Добавить endpoints для Reflection history
7.4. Добавить WebSocket для real-time updates

**Критерий готовности:**
- Все метрики Brain доступны через API

---

### 🔥 ЭТАП 8: Тестирование

**Файл:** `tests/xray/test_brain.py` (новый)

**Подзадачи:**
8.1. Unit-тесты для XRayBrain.decide()
8.2. Unit-тесты для MetaLearner
8.3. Unit-тесты для ReflectionLoop
8.4. Интеграционные тесты Brain + Pipeline
8.5. Тесты на self-learning (система улучшает решения со временем)

**Критерий готовности:**
- Все тесты проходят
- Система демонстрирует обучение

---

## 📁 СТРУКТУРА ФАЙЛОВ

```
backend/core/xray/
├── __init__.py              # Обновить экспорты
├── brain.py                 # НОВОЕ: Decision Engine
├── system_state.py          # НОВОЕ: System State
├── meta_learner.py          # НОВОЕ: Meta-Learning
├── reflection.py            # НОВОЕ: Reflection Loop
├── cognitive_state.py       # СУЩЕСТВУЕТ: Интегрировать
├── trace_context.py         # СУЩЕСТВУЕТ: Оставить
├── event_buffer.py          # СУЩЕСТВУЕТ: Оставить
├── insights.py              # СУЩЕСТВУЕТ: Интегрировать
├── broadcaster.py           # СУЩЕСТВУЕТ: Оставить
├── history_recorder.py      # СУЩЕСТВУЕТ: Оставить
├── thought_visualizer.py    # СУЩЕСТВУЕТ: Оставить
├── trace_collector.py       # СУЩЕСТВУЕТ: Оставить
└── validator.py             # СУЩЕСТВУЕТ: Оставить
```

---

## 🔄 ЗАВИСИМОСТИ МЕЖДУ КОМПОНЕНТАМИ

```
                    ┌─────────────────┐
                    │   User Input    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   X-Ray Brain   │◄──── System State
                    │  (Decision)     │
                    └────────┬────────┘
                             │ Decision
                    ┌────────▼────────┐
                    │    Pipeline     │
                    │   (Executor)    │
                    └────────┬────────┘
                             │ Result
                    ┌────────▼────────┐
                    │    LLM + Mem    │
                    └────────┬────────┘
                             │ Response
                    ┌────────▼────────┐
                    │ Response Guard  │
                    └────────┬────────┘
                             │ Final Response
                    ┌────────▼────────┐
                    │    User         │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    TruthLoop    │
                    └────────┬────────┘
                             │ Verification
                    ┌────────▼────────┐
                    │  Reflection     │──► Meta-Learner
                    │    Loop         │
                    └─────────────────┘
```

---

## 🎯 КЛЮЧЕВЫЕ РЕШЕНИЯ BRAIN

### 1. Strategy Selection

```python
def _choose_strategy(self, text: str, state: SystemState) -> str:
    """
    Стратегии:
    - simple: Прямой ответ (приветствия, простые вопросы)
    - retrieval: Поиск + синтез (фактологические вопросы)
    - reasoning: Логический анализ (сложные вопросы "почему")
    - creative: Творческая генерация (креативные запросы)
    - reflective: Саморефлексия (вопросы о системе)
    - learning: Обучение (запросы на запоминание)
    """
```

### 2. Model Selection

```python
def _select_model(self, decision: Decision) -> str:
    """
    На основе стратегии:
    - simple → cheap models (groq/llama-3.1-8b)
    - retrieval → mid models (groq/llama-3.1-70b)
    - reasoning → smart models (gpt-4, claude-3-sonnet)
    - creative → balanced models (gemini-2.0-flash)
    """
```

### 3. Memory Decision

```python
def _should_use_memory(self, text: str) -> dict:
    """
    Решения:
    - use_rag: bool
    - use_facts: bool
    - use_episodic: bool
    - use_semantic: bool
    - use_vector: bool
    """
```

### 4. Verification Decision

```python
def _should_verify(self, decision: Decision) -> bool:
    """
    Верифицировать если:
    - Стратегия = reasoning (сложные утверждения)
    - Уверенность < 0.6
    - Запрос содержит фактологические утверждения
    """
```

---

## 📊 METRICS & MONITORING

### Brain Metrics

```python
@dataclass
class BrainMetrics:
    total_decisions: int
    strategy_distribution: Dict[str, int]
    avg_confidence: float
    avg_response_time_ms: float
    learning_improvements: int  # Сколько раз система улучшила решение
    strategy_success_rates: Dict[str, float]  # % успеха по стратегиям
```

### API для мониторинга

```
GET /api/v1/xray/brain/metrics
{
    "total_decisions": 1250,
    "strategy_distribution": {
        "simple": 450,
        "retrieval": 320,
        "reasoning": 280,
        "creative": 150,
        "reflective": 50
    },
    "avg_confidence": 0.78,
    "strategy_success_rates": {
        "simple": 0.95,
        "retrieval": 0.82,
        "reasoning": 0.71,
        "creative": 0.88
    }
}
```

---

## 🧪 TEST SCENARIOS

### Scenario 1: Simple Greeting
```
Input: "Привет"
Expected Decision:
  - strategy: simple
  - model: cheap
  - use_memory: false
  - use_verification: false
```

### Scenario 2: Complex Question
```
Input: "Почему квантовая физика противоречит классической?"
Expected Decision:
  - strategy: reasoning
  - model: smart (gpt-4)
  - use_memory: true (rag + facts)
  - use_verification: true
```

### Scenario 3: Learning Request
```
Input: "Запомни, что я люблю кофе"
Expected Decision:
  - strategy: learning
  - model: mid
  - use_memory: true (episodic + facts)
  - use_verification: false
```

---

## 🚀 MIGRATION STRATEGY

### Phase 1: Parallel Run
- Brain работает параллельно с текущей системой
- Сравниваются решения
- Постепенное увеличение доверия к Brain

### Phase 2: Gradual Takeover
- Brain принимает решения для X% запросов
- Постепенное увеличение до 100%

### Phase 3: Full Integration
- Brain — единственный источник решений
- Pipeline — чистый исполнитель

---

## 📈 SUCCESS METRICS

| Метрика | До | После | Ц