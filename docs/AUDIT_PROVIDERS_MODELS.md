# АУДИТ: Загрузка и работа провайдеров-моделей

**Дата:** 09.05.2026
**Цель:** Найти проблемы, конфликты и ошибки в системе загрузки и работы провайдеров и моделей LLM

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (Блокируют работу)

### 1. ✖️ Функция `_get_text` передаётся как Callable, а не результат
**Файл:** `backend/api/frontend_routes.py`  
**Строки:** 892, 1037, 1080, 1662  
В строках 1037, 1080, 1662 передаётся `prompt=_get_text` (объект-функция), а не `prompt=_get_text(request)` (результат вызова).  
**Результат:** В LiteLLM отправляется строковое представление функции → ответы не соответствуют запросам.

### 2. ✖️ `is_fast_mode` хардкод `False` — код быстрого режима мёртв
**Файл:** `backend/api/frontend_routes.py`, строка 1030  
`use_fast_mode = False` — все запросы идут через Pipeline. Блок `if use_fast_mode:` (строки 1033-1058) никогда не выполняется.

### 3. ✖️ Дублированный блок получения ключа в chat endpoint
**Файл:** `backend/api/frontend_routes.py`, строки 950-961  
Два последовательных `if result.data:` — второй перезаписывает provider/model поверх первого.

### 4. ✖️ `getAvailableModels()` фильтрует ВСЕ модели с cost='unknown'
**Файл:** `frontend/src/services/modelCache.js`, строки 127-151  
Фильтр `cost === 'free' || cost === 'low'` отсекает все модели из `_get_fallback_models()` с `cost='unknown'` → пустой select.

### 5. ✖️ Дублирование `getAuthToken()` — конфликт имён
**Файлы:** `frontend/src/services/api.js` (строка 13) и `frontend/src/pages/ProvidersPage.jsx` (строка 143)

---

## 🟠 ВЫСОКИЙ ПРИОРИТЕТ

### 6. Четыре независимых системы загрузки списка моделей
1. `litellm_service.py` `get_available_models()` — через `litellm.model_cost`
2. `litellm_service.py` `_get_fallback_models()` — хардкод на 1000+ строк
3. `frontend_routes.py` `list_providers()` — сборка из `PROVIDER_META`
4. `ProvidersPage.jsx` `fallbackProviders`/`fallbackModels` — полностью статика

### 7. Dependencies Container регистрирует LiteLLMService как singleton
**Файл:** `backend/core/dependencies.py`, строка 167 — singleton, но `session_provider_manager.py` (строка 92) создаёт новый экземпляр.

### 8. Pipeline создаёт новый LiteLLMService на каждый запрос
**Файл:** `backend/core/pipeline.py`, строка 755: `litellm = LiteLLMService(api_key=user_api_key)`

### 9. Dependencies Container не используется в рантайме
**Файл:** `backend/core/dependencies.py` — все используют глобальные `if _instance is None`.

### 10. `session_provider_manager.py` импортирует `runtime.litellm_service`
**Файл:** `backend/runtime/session_provider_manager.py`, строка 8 — `runtime` не стандартный пакет.

---

## 🟡 СРЕДНИЙ ПРИОРИТЕТ

### 11. Дублирование `/health` endpoint
**Файл:** `backend/main.py`, строки 656-663 и 717-761.

### 12. `SessionProviderManager` не thread-safe
**Файл:** `backend/runtime/session_provider_manager.py` — глобальные переменные без блокировок.

### 13. `test_key_direct` всегда возвращает 400
**Файл:** `backend/api/frontend_routes.py`, строка 864-871.

### 14. GigaChat: двойная обработка имени модели
**Файл:** `backend/runtime/litellm_service.py`, строки 546-554 — `GigaChat-2-Lite` превращается в `GigaChat`.

### 15. `_generate_gigachat()` переопределяет messages (строка 627)
**Файл:** `backend/runtime/litellm_service.py`, строка 627-630. Создаётся новый `messages = []`, игнорирующий переданный контекст. **Результат:** GigaChat теряет историю диалога.

### 16. GigaChat — нет record_failure() при исключениях
**Файл:** `backend/runtime/litellm_service.py`, `_generate_gigachat()` — строки 603, 634. Исключения выбрасываются без `record_failure()`.

### 17. `generate_stream()` — нет CircuitBreaker и Timeout
**Файл:** `backend/runtime/litellm_service.py`, строки 742-816. В отличие от `generate()`, нет `before_request()`, `wait_for(timeout)`, `record_success/failure`.

### 18. `_get_full_model_name()` может заменить модель на DEFAULT_MODELS
**Файл:** `backend/runtime/litellm_service.py`, строка 283-301. Если model == provider или "auto" — подставляется дефолт.

### 19. Pipeline обращается к векторной памяти при каждом запросе
**Файл:** `backend/core/pipeline.py`, строки 524-543, 918-953. +200-500ms к каждому ответу.

### 20. `modelCache.js` TTL = 24 часа, бэкенд кэширует на 1 час
**Файлы:** `modelCache.js` строка 7 (24ч) vs `frontend_routes.py` строка 1826 (1ч).

### 21. DEFAULT_MODELS дублируется в 2 местах
**Файлы:** `litellm_service.py` строки 283-292 и `frontend_routes.py` строки 966-975.

---

## 🟢 НИЗКИЙ ПРИОРИТЕТ

### 22. `ProvidersPage.jsx` — статус "Connected" мерцает в "Active"
### 23. `ConnectionManager` не resilient при разрыве WebSocket
### 24. `background_initialization()` с silent catch
### 25. Тройная настройка CORS (CORSMiddleware + force_cors_headers)
### 26. GigaChat-пользователи не могут использовать другие провайдеры

---

## 📊 СВОДКА

| Категория | Количество |
|-----------|-----------|
| 🔴 Критические | 5 |
| 🟠 Высокие | 5 |
| 🟡 Средние | 11 |
| 🟢 Низкие | 5 |
| **Всего** | **26** |

*Аудит проведён на основе анализа исходного кода.*