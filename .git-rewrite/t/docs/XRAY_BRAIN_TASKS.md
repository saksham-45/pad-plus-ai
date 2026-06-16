# 🧠 X-Ray Brain — Конкретные задачи для AI-инженера

> **Главный принцип:** X-Ray Brain должен не только решать — он должен **ПЕРЕОПРЕДЕЛЯТЬ pipeline**

---

## 📌 ЗАДАЧА 0 — Создать ядро Brain (1 день максимум)

**Файл:** `backend/core/xray/brain.py`

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Decision:
    """Решение X-Ray Brain"""
    strategy: str              # simple, retrieval, reasoning, creative, reflective, learning
    model: str                 # модель LLM
    use_memory: bool           # использовать ли память
    depth: int                 # глубина анализа (1-5)
    use_verification: bool     # нужна ли верификация
    tone: str                  # тон ответа
    confidence: float          # уверенность решения
    reasoning: str             # обоснование

class XRayBrain:
    """🧠 X-Ray Brain — центр принятия решений"""
    
    def decide(self, input_text: str, context: dict) -> Decision:
        """Главный метод принятия решений"""
        pass
    
    def _choose_strategy(self, text: str) -> str:
        """Выбор стратегии обработки"""
        pass
    
    def _select_model(self, strategy: str) -> str:
        """Выбор LLM модели"""
        pass
    
    def _should_use_memory(self, text: str) -> bool:
        """Решение об использовании памяти"""
        pass
    
    def _estimate_depth(self, text: str) -> int:
        """Оценка необходимой глубины анализа"""
        pass
```

### Подзадачи:
- [ ] 0.1 Создать `backend/core/xray/brain.py`
- [ ] 0.2 Реализовать `Decision` dataclass
- [ ] 0.3 Реализовать `_choose_strategy()` — анализ текста + эвристики
- [ ] 0.4 Реализовать `_select_model()` — интеграция с ModelRouter
- [ ] 0.5 Реализовать `_should_use_memory()` — решение об использовании RAG/facts
- [ ] 0.6 Реализовать `_estimate_depth()` — оценка сложности запроса
- [ ] 0.7 Добавить глобальный экземпляр `get_xray_brain()`

### Критерий готовности:
```python
# Brain работает
brain = get_xray_brain()
decision = brain.decide("Почему небо голубое?", {})
assert decision.strategy == "reasoning"
assert decision.use_memory == True
assert decision.use_verification == True
```

---

## 📌 ЗАДАЧА 1 — УБИТЬ ЛОГИКУ В PIPELINE (самое важное)

**Файл:** `backend/core/pipeline.py`

### Что НАЙТИ и УДАЛИТЬ:

```python
# ❌ УДАЛИТЬ эти вызовы:
strategy = meta.decide_strategy(user_message)      # meta_controller
thinking_mode = budget.allocate(user_message)       # cognitive_budget
selected_model = router.select(thinking_mode.value) # model_router
```

### Чем ЗАМЕНИТЬ:

```python
# ✅ ЗАМЕНИТЬ на:
from core.xray.brain import get_xray_brain

brain = get_xray_brain()
decision = brain.decide(user_message, context)

# Использовать decision для всей обработки
strategy = decision.strategy
model = decision.model
use_memory = decision.use_memory
use_verification = decision.use_verification
```

### Подзадачи:
- [ ] 1.1 Найти все вызовы `meta_controller.decide_strategy()` — удалить
- [ ] 1.2 Найти все вызовы `cognitive_budget.allocate()` — удалить
- [ ] 1.3 Найти все вызовы `model_router.select()` — удалить
- [ ] 1.4 Добавить вызов `xray_brain.decide()` в начале `execute()`
- [ ] 1.5 Переписать логику retrieve: выполнять только если `decision.use_memory`
- [ ] 1.6 Переписать логику generate: использовать `decision.model`
- [ ] 1.7 Переписать логику verify: выполнять только если `decision.use_verification`

### До (упрощённо):
```python
async def execute(self, user_message, context):
    # Pipeline сам принимает решения
    strategy = meta.decide_strategy(user_message)
    model = router.select(strategy)
    # ... выполнение ...
```

### После:
```python
async def execute(self, user_message, context):
    # Brain принимает решения
    decision = xray_brain.decide(user_message, context)
    
    # Выполнение по инструкции Brain
    if decision.use_memory:
        # retrieve context
        pass
    
    # generate с decision.model
    result = await litellm.generate(model=decision.model, ...)
    
    if decision.use_verification:
        # verify
        pass
    
    return result
```

### Критерий готовности:
- [ ] Pipeline не содержит if/else для выбора стратегии
- [ ] Все решения приходят из X-Ray Brain
- [ ] Pipeline — чистый исполнитель

---

## 📌 ЗАДАЧА 2 — SystemState (минимум, но рабочий)

**Файл:** `backend/core/xray/system_state.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Any
import time

@dataclass
class SystemState:
    """Текущее состояние системы"""
    load: float = 0.0              # 0.0 - 1.0
    confidence: float = 1.0        # 0.0 - 1.0
    recent_errors: int = 0         # последние ошибки
    active_sessions: int = 0       # активные сессии
    last_updated: float = field(default_factory=time.time)
    
    def update_from_result(self, result: dict):
        """Обновляет состояние из результата pipeline"""
        self.confidence = result.get('confidence', 0.5)
        if not result.get('success', True):
            self.recent_errors += 1
        self.last_updated = time.time()
    
    def get_snapshot(self) -> dict:
        """Возвращает снимок состояния"""
        return {
            "load": self.load,
            "confidence": self.confidence,
            "recent_errors": self.recent_errors,
            "active_sessions": self.active_sessions
        }
    
    def should_simplify(self) -> bool:
        """Определяет, нужно ли упростить стратегию"""
        return self.load > 0.8 or self.recent_errors > 5

class SystemStateManager:
    """Управляет состоянием системы"""
    
    def __init__(self):
        self._state = SystemState()
    
    def get_state(self) -> SystemState:
        return self._state
    
    def update(self, result: dict):
        self._state.update_from_result(result)
```

### Подзадачи:
- [ ] 2.1 Создать `backend/core/xray/system_state.py`
- [ ] 2.2 Реализовать `SystemState` dataclass
- [ ] 2.3 Реализовать `update_from_result()` — обновление из pipeline result
- [ ] 2.4 Реализовать `should_simplify()` — решение об упрощении
- [ ] 2.5 Добавить глобальный экземпляр `get_system_state_manager()`
- [ ] 2.6 Интегрировать в Brain: `brain.decide()` принимает state

### Критерий готовности:
```python
# Стратегия меняется при высокой нагрузке
state = get_system_state_manager().get_state()
state.load = 0.9  # высокая нагрузка

decision = brain.decide("Сложный вопрос", state.get_snapshot())
assert decision.strategy == "simple"  # упрощено из-за нагрузки
```

---

## 📌 ЗАДАЧА 3 — Meta-Learner (упрощённый, но реальный)

**Файл:** `backend/core/xray/meta_learner.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os
import time

@dataclass
class StrategyStats:
    """Статистика по стратегии"""
    success: int = 0
    fail: int = 0
    total_confidence: float = 0.0
    count: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.count == 0:
            return 0.0
        return self.success / self.count
    
    @property
    def avg_confidence(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_confidence / self.count

class MetaLearner:
    """Система мета-обучения"""
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = "data/xray_meta_learner.json"
        self.data_path = data_path
        self.stats: Dict[str, StrategyStats] = {
            "simple": StrategyStats(),
            "retrieval": StrategyStats(),
            "reasoning": StrategyStats(),
            "creative": StrategyStats(),
            "reflective": StrategyStats(),
            "learning": StrategyStats(),
        }
        self._load()
    
    def record_outcome(self, strategy: str, result: dict):
        """Записывает результат выполнения"""
        if strategy not in self.stats:
            return
        
        stats = self.stats[strategy]
        stats.count += 1
        
        if result.get('success', False):
            stats.success += 1
        else:
            stats.fail += 1
        
        stats.total_confidence += result.get('confidence', 0.5)
        self._save()
    
    def get_strategy_stats(self, strategy: str) -> StrategyStats:
        """Возвращает статистику по стратегии"""
        return self.stats.get(strategy, StrategyStats())
    
    def get_best_strategy(self, min_samples: int = 5) -> Optional[str]:
        """Возвращает лучшую стратегию по success rate"""
        candidates = {
            s: stats 
            for s, stats in self.stats.items() 
            if stats.count >= min_samples
        }
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda x: x[1].success_rate)
    
    def should_adjust_strategy(self, current: str) -> Optional[str]:
        """Рекомендует смену стратегии если текущая плохо работает"""
        current_stats = self.stats.get(current)
        if not current_stats or current_stats.count < 5:
            return None
        
        # Если success rate < 0.5 — рекомендовать другую
        if current_stats.success_rate < 0.5:
            best = self.get_best_strategy()
            if best and best != current:
                return best
        
        return None
    
    def _load(self):
        """Загружает статистику из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    for strategy, stats_data in data.items():
                        if strategy in self.stats:
                            self.stats[strategy].success = stats_data.get('success', 0)
                            self.stats[strategy].fail = stats_data.get('fail', 0)
                            self.stats[strategy].total_confidence = stats_data.get('total_confidence', 0.0)
                            self.stats[strategy].count = stats_data.get('count', 0)
            except:
                pass
    
    def _save(self):
        """Сохраняет статистику в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data = {
            strategy: {
                'success': stats.success,
                'fail': stats.fail,
                'total_confidence': stats.total_confidence,
                'count': stats.count
            }
            for strategy, stats in self.stats.items()
        }
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

# Глобальный экземпляр
_meta_learner = None

def get_meta_learner() -> MetaLearner:
    global _meta_learner
    if _meta_learner is None:
        _meta_learner = MetaLearner()
    return _meta_learner
```

### Подзадачи:
- [ ] 3.1 Создать `backend/core/xray/meta_learner.py`
- [ ] 3.2 Реализовать `StrategyStats` dataclass
- [ ] 3.3 Реализовать `record_outcome()` — запись результатов
- [ ] 3.4 Реализовать `get_best_strategy()` — лучшая стратегия
- [ ] 3.5 Реализовать `should_adjust_strategy()` — рекомендации
- [ ] 3.6 Добавить сохранение/загрузку статистики
- [ ] 3.7 Добавить глобальный экземпляр `get_meta_learner()`

### Критерий готовности:
```python
# Стратегия адаптируется после 10+ запросов
learner = get_meta_learner()

# Записываем результаты
learner.record_outcome("reasoning", {"success": False, "confidence": 0.3})
learner.record_outcome("simple", {"success": True, "confidence": 0.9})

# После 10+ запросов система предлагает сменить стратегию
adjustment = learner.should_adjust_strategy("reasoning")
if adjustment:
    print(f"Рекомендуется сменить стратегию на: {adjustment}")
```

---

## 📌 ЗАДАЧА 4 — Reflection Loop (обязательно)

**Файл:** `backend/core/xray/reflection.py`

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("padplus.xray")

@dataclass
class ReflectionResult:
    """Результат рефлексии"""
    confidence_gap: float        # разница между ожидаемой и фактической
    success: bool
    lessons: list               # извлечённые уроки
    should_adjust: bool         # нужно ли корректировать стратегию

class ReflectionLoop:
    """Контур рефлексии"""
    
    def reflect(self, decision: dict, result: dict) -> ReflectionResult:
        """Анализирует результат и обновляет систему"""
        from core.xray.meta_learner import get_meta_learner
        
        # 1. Оцениваем результат
        confidence_gap = self._analyze_confidence_gap(decision, result)
        success = result.get('success', False)
        
        # 2. Извлекаем уроки
        lessons = self._extract_lessons(decision, result)
        
        # 3. Обновляем мета-обучение
        meta = get_meta_learner()
        meta.record_outcome(decision.get('strategy', 'simple'), result)
        
        # 4. Проверяем, нужно ли корректировать
        should_adjust = meta.should_adjust_strategy(decision.get('strategy', 'simple')) is not None
        
        reflection = ReflectionResult(
            confidence_gap=confidence_gap,
            success=success,
            lessons=lessons,
            should_adjust=should_adjust
        )
        
        # 5. Логируем
        logger.info(
            f"🧠 Reflection: strategy={decision.get('strategy')}, "
            f"success={success}, confidence_gap={confidence_gap:.2f}, "
            f"should_adjust={should_adjust}"
        )
        
        return reflection
    
    def _analyze_confidence_gap(self, decision: dict, result: dict) -> float:
        """Анализирует разрыв между ожидаемой и фактической уверенностью"""
        expected = decision.get('confidence', 0.5)
        actual = result.get('confidence', 0.5)
        return actual - expected
    
    def _extract_lessons(self, decision: dict, result: dict) -> list:
        """Извлекает уроки из результата"""
        lessons = []
        
        # Урок 1: если низкая уверенность — нужно больше памяти
        if result.get('confidence', 0) < 0.5 and not decision.get('use_memory', False):
            lessons.append("Низкая уверенность — использовать память")
        
        # Урок 2: если ошибка — упростить стратегию
        if not result.get('success', True):
            lessons.append("Ошибка — рассмотреть упрощение стратегии")
        
        # Урок 3: если высокая нагрузка — упростить
        if result.get('cognitive_load', 0) > 0.8:
            lessons.append("Высокая нагрузка — упростить обработку")
        
        return lessons

# Глобальный экземпляр
_reflection = None

def get_reflection_loop() -> ReflectionLoop:
    global _reflection
    if _reflection is None:
        _reflection = ReflectionLoop()
    return _reflection
```

### Подзадачи:
- [ ] 4.1 Создать `backend/core/xray/reflection.py`
- [ ] 4.2 Реализовать `ReflectionResult` dataclass
- [ ] 4.3 Реализовать `reflect()` — главный метод
- [ ] 4.4 Реализовать `_analyze_confidence_gap()` — анализ разрыва
- [ ] 4.5 Реализовать `_extract_lessons()` — извлечение уроков
- [ ] 4.6 Интегрировать с MetaLearner
- [ ] 4.7 Добавить глобальный экземпляр `get_reflection_loop()`

### Критерий готовности:
```python
# Каждый ответ влияет на будущие решения
reflection = get_reflection_loop()

decision = {"strategy": "reasoning", "confidence": 0.8}
result = {"success": True, "confidence": 0.6}

reflection_result = reflection.reflect(decision, result)
assert reflection_result.success == True
assert reflection_result.confidence_gap < 0  # уверенность ниже ожидаемой
```

---

## 📌 ЗАДАЧА 5 — ЖЁСТКАЯ ИНТЕГРАЦИЯ (ключевой шаг)

**Изменения в `backend/core/pipeline.py`:**

### Новый flow:

```python
async def execute(self, user_message, context):
    # 1. Brain принимает решение
    from core.xray.brain import get_xray_brain
    from core.xray.reflection import get_reflection_loop
    from core.xray.system_state import get_system_state_manager
    
    brain = get_xray_brain()
    reflection = get_reflection_loop()
    state_manager = get_system_state_manager()
    
    # Получаем состояние системы
    state = state_manager.get_state().get_snapshot()
    
    # Brain решает
    decision = brain.decide(user_message, context)
    
    try:
        # 2. Pipeline выполняет (только выполняет!)
        result = await self._execute_with_decision(decision, user_message, context)
        
        # 3. Reflection анализирует
        reflection.reflect(decision.to_dict(), result.to_dict())
        
        # 4. Обновляем состояние
        state_manager.update(result.to_dict())
        
        return result
        
    except Exception as e:
        # Fallback при ошибке
        logger.error(f"Pipeline error: {e}")
        return self._create_error_result(str(e))
```

### Подзадачи:
- [ ] 5.1 Создать метод `_execute_with_decision()` — выполнение по решению Brain
- [ ] 5.2 Интегрировать вызов `brain.decide()` в начало `execute()`
- [ ] 5.3 Интегрировать вызов `reflection.reflect()` после выполнения
- [ ] 5.4 Интегрировать вызов `state_manager.update()` для обновления состояния
- [ ] 5.5 Добавить fallback при ошибке Brain

### Критерий готовности:
- [ ] Есть замкнутый цикл: `decision → execution → reflection → learning`
- [ ] Pipeline не принимает решений
- [ ] Состояние обновляется после каждого запроса

---

## 📌 ЗАДАЧА 6 — ЛОГИРОВАНИЕ МЫШЛЕНИЯ (X-Ray = видимый мозг)

**Изменения в `backend/core/pipeline.py`:**

### Добавить в каждый ответ:

```python
result.metadata["xray_decision"] = {
    "strategy": decision.strategy,
    "model": decision.model,
    "confidence": decision.confidence,
    "memory_used": decision.use_memory,
    "verification_used": decision.use_verification,
    "reasoning": decision.reasoning
}
```

### Логировать:

```python
logger.info(
    f"🧠 X-Ray Decision:\n"
    f"  strategy: {decision.strategy}\n"
    f"  model: {decision.model}\n"
    f"  memory: {decision.use_memory}\n"
    f"  verification: {decision.use_verification}\n"
    f"  confidence: {decision.confidence:.2f}\n"
    f"  reasoning: {decision.reasoning}"
)
```

### Подзадачи:
- [ ] 6.1 Добавить `xray_decision` в `result.metadata`
- [ ] 6.2 Добавить логирование решения Brain
- [ ] 6.3 Добавить логирование Reflection результата

### Критерий готовности:
```
🧠 X-Ray Decision:
  strategy: reasoning
  model: gpt-4
  memory: true
  verification: true
  confidence: 0.74
  reasoning: Сложный вопрос требует глубокого анализа
```

---

## 📌 ЗАДАЧА 7 — FAIL-SAFE (иначе система сломается)

**Изменения в `backend/core/xray/brain.py`:**

```python
def decide(self, input_text: str, context: dict) -> Decision:
    """Главный метод с fallback"""
    try:
        return self._decide_internal(input_text, context)
    except Exception as e:
        logger.error(f"Brain decision error: {e}")
        # Fallback на простую стратегию
        return Decision(
            strategy="simple",
            model="groq/llama-3.1-8b-instant",
            use_memory=False,
            depth=1,
            use_verification=False,
            tone="neutral",
            confidence=0.5,
            reasoning=f"Fallback из-за ошибки: {e}"
        )

def _select_model(self, strategy: str) -> str:
    """Выбор модели с fallback"""
    try:
        from core.agi.model_router import get_model_router
        router = get_model_router()
        return router.select(strategy)
    except Exception as e:
        logger.warning(f"Model router error: {e}, using default")
        return "groq/llama-3.1-70b-versatile"  # Default fallback
```

### Подзадачи:
- [ ] 7.1 Обернуть `decide()` в try/except с fallback
- [ ] 7.2 Добавить fallback в `_select_model()`
- [ ] 7.3 Добавить fallback в `_choose_strategy()` при высокой нагрузке
- [ ] 7.4 Добавить проверку confidence < 0.3 → fallback на reasoning

### Критерий готовности:
- [ ] Система НЕ падает никогда
- [ ] При ошибке Brain используется simple стратегия
- [ ] При недоступности модели используется fallback модель

---

## 🚀 РЕАЛЬНЫЙ ПОРЯДОК ВНЕДРЕНИЯ

```
1. Brain (работающий)           — 1 день
2. Pipeline → executor only     — 1 день  
3. Reflection (логирование)     — 0.5 дня
4. Meta-learning (адаптация)    — 0.5 дня
5. System state (оптимизация)   — 0.5 дня

ИТОГО: ~3.5 дней
```

---

## ✅ CHECKLIST ГОТОВНОСТИ

- [ ] Brain принимает решения
- [ ] Pipeline только исполняет
- [ ] Reflection анализирует результаты
- [ ] Meta-learner запоминает и адаптирует
- [ ] System state отслеживает нагрузку
- [ ] Логирование показывает "мышление"
- [ ] Fail-safe работает
- [ ] Замкнутый цикл: decision → execution → reflection → learning

---

## 🧠 ФИНАЛЬНАЯ МЫСЛЬ

> Ты строишь **СИСТЕМУ, КОТОРАЯ ПРИНИМАЕТ РЕШЕНИЯ О СВОЁМ МЫШЛЕНИИ**

Это не просто AI ассистент. Это AI, который:
- **Решает** как думать
- **Учится** на своих решениях
- **Адаптируется** к изменениям
- **Рефлексирует** над результатами

Это уровень真正的 Cognitive Architecture.