# 🛡️ ResponseGuard Production Implementation Plan

## 📋 Текущее состояние системы

### ✅ Что уже работает:
1. **Базовый ResponseGuard** (`backend/core/guard/response_guard.py`)
   - Замена запрещённых фраз ("языковая модель" → "PAD+ AI")
   - Удаление дублей идентичности
   - Базовая нормализация текста

2. **Эмоциональная модель** (`backend/emotion/pad_model.py`)
   - PAD параметры (pleasure, arousal, dominance)
   - Дополнительные параметры (curiosity, confidence, social_connection)
   - Метод `get_style()` для определения тона общения

3. **Pipeline** (`backend/core/pipeline.py`)
   - Полноценный пайплайн с 14 этапами
   - Интеграция ResponseGuard в конце обработки
   - Мета-данные для отслеживания confidence, strategy, sources

### ❌ Что нужно реализовать:

## 🎯 Цели реализации

### 1️⃣ Многоступенчатый ResponseGuard (6 ступеней)
```
RAW LLM OUTPUT
    ↓
[1] Sanitize (базовая очистка)
    ↓
[2] Anti-Repeat / Anti-Spam (убираем дубли)
    ↓
[3] Identity Control (контроль идентичности)
    ↓
[4] Style & Persona Normalize (нормализация стиля)
    ↓
[5] Safety / Toxicity (фильтр безопасности)
    ↓
[6] Structure Fix (финальная чистка)
    ↓
FINAL RESPONSE
```

### 2️⃣ Self-Healing Guard (самообучение)
- Детектор ошибок (identity_spam, repetition, too_long)
- Память паттернов (GuardMemory)
- Адаптация правил (adapt_guard)

### 3️⃣ Adaptive Tone Engine (эмоциональные ответы)
- Маппинг эмоций → префиксы и стили
- Вариативность префиксов
- Интеграция с PAD моделью

### 4️⃣ Cognitive Layer (объяснение мышления)
- Генерация cognition meta
- Режимы: basic / debug
- Интеграция в API ответ

---

## 📝 План реализации

### 🔧 ЗАДАЧА 1: Многоступенчатый ResponseGuard

**Файл:** `backend/core/guard/response_guard.py`

**Изменения:**
1. Добавить метод `_sanitize()` - базовая очистка
2. Добавить метод `_remove_repetition()` - анти-повторы
3. Добавить метод `_fix_identity()` - контроль идентичности с meta
4. Добавить метод `_normalize_style()` - нормализация стиля
5. Добавить метод `_safety_filter()` - фильтр безопасности
6. Добавить метод `_final_cleanup()` - финальная чистка
7. Обновить `process()` для приёма meta параметров
8. Добавить confidence-based rewrite

**Критерий готовности:**
- Все 6 ступеней работают последовательно
- Контроль идентичности учитывает is_first_message и asked_identity
- Нет дублей "Я — PAD+ AI"
- Чистый, нормализованный текст

---

### 🔧 ЗАДАЧА 2: Self-Healing Guard

**Файл:** `backend/core/guard/self_healing.py` (новый)

**Компоненты:**
1. `GuardErrorDetector` - классификация ошибок
   - identity_spam (множественные "Я — PAD+ AI")
   - repetition (повторяющиеся фразы)
   - too_long (ответ > 2000 символов)

2. `GuardMemory` - хранение паттернов
   - In-memory хранилище
   - SQLite fallback для персистентности
   - Подсчёт частоты ошибок

3. `adapt_guard()` - адаптация правил
   - Ужесточение identity контроля при identity_spam > 5
   - Включение дедупликации при repetition > 5

**Критерий готовности:**
- Система логирует ошибки
- Guard меняет поведение при накоплении ошибок
- Паттерны сохраняются между сессиями

---

### 🔧 ЗАДАЧА 3: Adaptive Tone Engine

**Файл:** `backend/core/guard/tone_engine.py` (новый)

**Компоненты:**
1. `TONE_MAP` - маппинг эмоций
   ```python
   {
       "joy": {"prefix": "Отличная новость —", "style": "warm"},
       "sadness": {"prefix": "Понимаю, это может быть тяжело —", "style": "supportive"},
       "anger": {"prefix": "Давай разберёмся спокойно —", "style": "calm"},
       "neutral": {"prefix": "", "style": "balanced"}
   }
   ```

2. `ToneEngine` класс
   - Метод `apply(text, emotion)` 
   - Случайный выбор префикса для вариативности
   - Интеграция с PAD моделью

**Критерий готовности:**
- Ответы различаются при разных эмоциях
- Нет повторяющихся шаблонов
- Префиксы соответствуют эмоциональному состоянию

---

### 🔧 ЗАДАЧА 4: Cognitive Layer

**Файл:** `backend/core/guard/cognitive_layer.py` (новый)

**Компоненты:**
1. `build_cognition(meta)` - генератор мета-данных
   ```json
   {
       "strategy": "retrieval",
       "confidence": 0.78,
       "memory_used": true
   }
   ```

2. Формат ответа:
   - Basic режим: только ответ
   - Debug режим: ответ + cognition

**Критерий готовности:**
- Можно включать/выключать объяснение мышления
- Cognition данные корректно генерируются из meta
- Интеграция в API ответ

---

### 🔧 ЗАДАЧА 5: Интеграция в Pipeline

**Файл:** `backend/core/pipeline.py`

**Изменения:**
1. После генерации ответа:
   ```
   LLM Response
   → ResponseGuard (6 ступеней)
   → Self-Healing (детекция + адаптация)
   → ToneEngine (применение эмоций)
   → CognitiveLayer (генерация мета-данных)
   → Final Response
   ```

2. Передать meta параметры:
   - `is_first_message`
   - `asked_identity`
   - `confidence`
   - `emotion`
   - `strategy`

3. Обновить `PipelineResult.to_dict()`:
   - Добавить cognition секцию
   - Добавить режим explain

**Критерий готовности:**
- Все компоненты работают последовательно
- Meta параметры корректно передаются
- API ответ включает cognition данные

---

### 🔧 ЗАДАЧА 6: Тестирование

**Файл:** `tests/hardening/test_response_guard_v2.py` (новый)

**Тест-кейсы:**
1. Многоступенчатая очистка
2. Контроль идентичности (first message vs subsequent)
3. Анти-повторы
4. Self-healing адаптация
5. Tone engine применение
6. Cognitive layer генерация

**Критерий готовности:**
- Все тесты проходят
- Покрытие > 90%
- Нет регрессий

---

## 🚀 Порядок реализации

1. **ЗАДАЧА 1** - Многоступенчатый ResponseGuard (базовый функционал)
2. **ЗАДАЧА 5** - Интеграция в Pipeline (чтобы всё работало вместе)
3. **ЗАДАЧА 6** - Тестирование (проверка работоспособности)
4. **ЗАДАЧА 2** - Self-Healing Guard (улучшение качества)
5. **ЗАДАЧА 3** - Adaptive Tone Engine (эмоциональность)
6. **ЗАДАЧА 4** - Cognitive Layer (объяснимость)

---

## 📊 Ожидаемые результаты

### ДО:
- ❌ "Я — PAD+ AI..." ×3
- ❌ Дубли фраз
- ❌ Ломаный текст
- ❌ Одинаковые ответы независимо от эмоций

### ПОСЛЕ:
- ✅ Чистая речь
- ✅ Контроль идентичности (1 раз в первом сообщении)
- ✅ Стабильный стиль
- ✅ Production-поведение
- ✅ Эмоционально окрашенные ответы
- ✅ Самообучение на ошибках
- ✅ Объяснение процесса мышления

---

## 🔥 Дальнейшее развитие

После реализации базового плана:

1. **Self-Healing Guard v2** - машинное обучение для классификации ошибок
2. **Adaptive Tone Engine v2** - контекстуальные эмоции (не только префиксы)
3. **Cognitive Layer v2** - пошаговое объяснение рассуждений
4. **ResponseGuard Analytics** - дашборд качества ответов

---

## 📚 Ресурсы

- [Исходный план от пользователя](#) (в запросе)
- [Текущий ResponseGuard](../backend/core/guard/response_guard.py)
- [Pipeline](../backend/core/pipeline.py)
- [PAD Model](../backend/emotion/pad_model.py)