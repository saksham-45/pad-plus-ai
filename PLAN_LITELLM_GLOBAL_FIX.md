# План: Глобальный LiteLLM — единая точка входа для всех пользователей PAD+ AI

**Цель:** Любой пользователь может выбрать провайдера и модель на странице Providers, и система работает без ошибок. Один глобальный LiteLLMService для всех, никаких пересозданий, правильная передача API ключей.

---

## 🔴 ШАГ 1: НЕМЕДЛЕННЫЕ ИСПРАВЛЕНИЯ (критические баги)

### 1.1 Исправить `_get_text` — передавать результат, а не функцию
**Файл:** `backend/api/frontend_routes.py`
- Заменить `prompt=_get_text` на `prompt=_get_text(request)` в строках 1037, 1080, 1662

### 1.2 Удалить дублированный блок получения ключа
**Файл:** `backend/api/frontend_routes.py`
- Удалить второй `if result.data:` (строки 956-961)

### 1.3 Исправить хардкод `use_fast_mode = False`
**Файл:** `backend/api/frontend_routes.py`
- Заменить `use_fast_mode = False` на `use_fast_mode = is_fast_request(user_message)`
- Функция `is_fast_request()` уже существует (строки 148-192)

### 1.4 Исправить `getAvailableModels()` — показывать все модели
**Файл:** `frontend/src/services/modelCache.js`
- Добавить `cost === 'unknown'` как допустимое значение в фильтр

### 1.5 Удалить дублирующуюся `getAuthToken()` из ProvidersPage
**Файл:** `frontend/src/pages/ProvidersPage.jsx`
- Удалить локальное объявление (строки 142-156)

---

## 🟠 ШАГ 2: ГЛОБАЛЬНЫЙ LITELLM — АРХИТЕКТУРА

### 2.1 Один глобальный LiteLLMService без api_key в конструкторе
**Файл:** `backend/runtime/litellm_service.py`
```python
class LiteLLMService:
    def __init__(self):
        self._timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        self._circuit_breaker = CircuitBreaker(...)
```
- Убрать `api_key` и `model` из `__init__`
- Circuit Breaker один на всё приложение

### 2.2 SessionProviderManager — получает ключи, не создаёт LiteLLMService
**Файл:** `backend/runtime/session_provider_manager.py`
- Методы: `get_user_api_key()`, `get_user_default_key()`, `has_provider_key()`
- Не создаёт `LiteLLMService`

### 2.3 Pipeline — использует глобальный LiteLLMService
**Файл:** `backend/core/pipeline.py`
- Удалить `LiteLLMService(api_key=user_api_key)` (строка 755)
- Использовать `get_litellm_service()`

### 2.4 chat endpoint — API ключ → LiteLLM
**Файл:** `backend/api/frontend_routes.py`
- Получает ключ из БД (без дублирования)
- Передаёт в `pipeline.execute()` или напрямую в `litellm_service.generate()`

---

## 🟡 ШАГ 3: УНИФИКАЦИЯ ЗАГРУЗКИ МОДЕЛЕЙ

### 3.1 Единый источник правды — `litellm_service.py`
- `get_available_models(provider=None)` — единственный метод
- Fallback: все **бесплатные** модели + 2-3 популярные платные на провайдера

### 3.2 Сократить дублирующиеся источники
- `_get_fallback_models()` — убрать 1000+ строк, оставить бесплатные + популярные
- Синхронизировать с `PROVIDER_META` и `fallbackProviders`

### 3.3 Синхронизировать TTL кэша
- `modelCache.js`: `24 * 60 * 60 * 1000` → `3600 * 1000` (1 час)

---

## 🔵 ШАГ 4: ИСПРАВЛЕНИЕ GIGACHAT И STREAMING

### 4.1 Не переименовывать модель
**Файл:** `backend/runtime/litellm_service.py`, строки 546-554
- Убрать логику: `"lite" → GigaChat`, `"pro" → GigaChat-Pro`
- Использовать модель как есть

### 4.2 Исправить обработку ключа GigaChat
- Сохранять полный credentials
- Правильное кодирование (упростить логику split на строке 557)

### 4.3 Добавить record_failure() при ошибках GigaChat
**Файл:** `backend/runtime/litellm_service.py` `_generate_gigachat()`
- Строка 603: добавить `record_failure()` перед `raise`
- Строка 634: добавить `record_failure()` перед `raise`

### 4.4 Исправить переопределение messages (строка 627)
**Файл:** `backend/runtime/litellm_service.py`, строки 627-630
- Удалить создание нового `messages = []`
- В `_send_chat()` использовать `messages`, переданный как параметр

### 4.5 Добавить CircuitBreaker + Timeout в generate_stream()
**Файл:** `backend/runtime/litellm_service.py`, строки 742-816
- `self._circuit_breaker.before_request()` перед запросом
- `asyncio.wait_for(..., timeout=self._timeout)`
- `record_success()` при успехе, `record_failure()` в `except`

---

## 🔵 ШАГ 5: DEFAULT_MODELS

### 5.1 Единый источник DEFAULT_MODELS
- Определить **только** в `litellm_service.py`
- В `frontend_routes.py` импортировать: `from runtime.litellm_service import DEFAULT_MODELS`

---

## 🟢 ШАГ 6: DI-КОНТЕЙНЕР

### 6.1 `get_litellm_service()` — единая точка доступа
- Убрать создание LiteLLMService в `dependencies.py`
- Убрать `from runtime.litellm_service import LiteLLMService` — везде `get_litellm_service()`

---

## 📋 ИТОГОВЫЙ СПИСОК ИЗМЕНЕНИЙ

| # | Файл | Что меняем | Приоритет |
|---|------|-----------|-----------|
| 1 | `frontend_routes.py` (3 места) | `_get_text` → `_get_text(request)` | 🔴 |
| 2 | `frontend_routes.py` | Удалить дубликат `if result.data:` | 🔴 |
| 3 | `frontend_routes.py` | `use_fast_mode = False` → `is_fast_request()` | 🔴 |
| 4 | `modelCache.js` | Фильтр + cost='unknown' | 🔴 |
| 5 | `ProvidersPage.jsx` | Удалить локальную `getAuthToken()` | 🔴 |
| 6 | `litellm_service.py` | Убрать api_key из __init__, оставить CircuitBreaker | 🟠 |
| 7 | `session_provider_manager.py` | Только получение ключей, не создавать LiteLLMService | 🟠 |
| 8 | `pipeline.py` | Не создавать LiteLLMService на каждый запрос | 🟠 |
| 9 | `pipeline.py` | Использовать `get_litellm_service()` | 🟠 |
| 10 | `litellm_service.py` | Сократить `_get_fallback_models()`: все бесплатные + 2-3 популярные | 🟡 |
| 11 | `ProvidersPage.jsx` | Сократить статику fallback | 🟡 |
| 12 | `modelCache.js` | TTL 24ч → 1ч | 🟡 |
| 13 | `litellm_service.py` | GigaChat: не переименовывать модель | 🟡 |
| 14 | `litellm_service.py` | GigaChat: добавить record_failure() при ошибках | 🟡 |
| 15 | `litellm_service.py` | GigaChat: исправить переопределение messages (строка 627) | 🟡 |
| 16 | `litellm_service.py` | generate_stream(): добавить CircuitBreaker + Timeout | 🟠 |
| 17 | `main.py` | Удалить дублирующийся `/health` | 🟡 |
| 18 | `litellm_service.py` + `frontend_routes.py` | DEFAULT_MODELS: единый источник (убрать дубль) | 🟡 |
| 19 | `dependencies.py` | Перевести на get_litellm_service(), убрать дубли | 🟢 |

**Итого:** 19 изменений в файлах.

---

## 🧪 ТЕСТИРОВАНИЕ ПОСЛЕ ИСПРАВЛЕНИЙ

1. Providers → отображаются все провайдеры
2. Выбрать провайдера → модели не пустые (free + популярные)
3. Ввести ключ → сохранить → "Connected"
4. Чат → ответ от выбранного провайдера
5. Сменить провайдера в чате → ответ от другого
6. GigaChat отдельно (контекст не теряется)
7. Streaming (`/chat/stream`) не зависает
8. "Привет" < 2 секунд (fast mode)

---

## 🔧 КРИТЕРИИ УСПЕХА

- ✅ Один `get_litellm_service()` во всём приложении
- ✅ Circuit Breaker один и работает (не пересоздаётся)
- ✅ Выпадающий список моделей не пустой
- ✅ Ответы соответствуют запросам
- ✅ GigaChat использует выбранную модель
- ✅ Быстрые запросы за 1-2 секунды