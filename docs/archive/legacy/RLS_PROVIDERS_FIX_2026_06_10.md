# Исправление RLS + Провайдеров

**Дата:** 2026-06-10  
**Приоритет:** P0 (Критический)  
**Статус:** ✅ Выполнено

## Проблема

POST `/api/v1/chat` с OpenRouter не находил пользовательский ключ и возвращал ошибку `API ключ не настроен`, даже если ключ был сохранён в БД.

## Корневая причина

1. **Дублирующая логика в `GeneratePhase`** — фаза пыталась получить ключ через `SessionProviderManager`, даже когда ключ уже был передан из `frontend_routes`
2. **Недостаточное логирование** — сложно было диагностировать на каком этапе теряется ключ
3. **Отсутствие fallback в pipeline** — при ошибке OpenRouter не использовался GigaChat

## Внесённые изменения

### 1. `backend/core/pipeline/phases/generate.py`

**До:**
```python
user_api_key = ctx.api_key
user_provider = ctx.provider

if not user_api_key and ctx.session_id:
    try:
        from runtime.session_provider_manager import get_session_manager
        session_manager = get_session_manager()
        user_manager = session_manager.create_user_manager(ctx.session_id)
        if user_manager.llm_service:
            user_api_key = user_manager.llm_service.default_api_key
    except Exception:
        pass
```

**После:**
```python
# Простая логика — используем только переданный ключ
user_api_key = ctx.api_key
user_provider = ctx.provider

logger.info(f"GeneratePhase: api_key={'***' if user_api_key else 'MISSING'}, provider={user_provider}")

# Используем ProviderManager с автоматическим fallback
pm = get_provider_manager()
gen_result = await pm.generate(
    prompt=ctx.user_message,
    system_prompt=full_context,
    api_key=user_api_key,
    model=model,
    provider=user_provider,
)
```

**Изменения:**
- ✅ Удалена дублирующая логика получения ключа через `SessionProviderManager`
- ✅ Добавлено детальное логирование
- ✅ Используется `ProviderManager` для автоматического fallback OpenRouter → GigaChat
- ✅ Передана модель из контекста

### 2. `backend/api/frontend_routes.py` — `chat` endpoint

**Улучшения логирования:**
```python
logger.info(f"Chat request: key_id={request.key_id}, model={request.model}, provider={request.provider}")

if request.key_id:
    logger.info(f"Looking up key_id: {request.key_id} for user {user_id}")
    # ... поиск ключа ...
    logger.info(f"✅ Key found: provider={key_data['provider']}, model={key_data.get('model_preference')}")
    logger.info(f"✅ Key decrypted, length={len(api_key)}")
else:
    logger.info("No key_id provided, searching for default key")

logger.info(f"✅ Using: provider={provider}, model={model}, key_length={len(api_key)}")
```

**Передача model_preference в pipeline:**
```python
result = await pipeline.execute(
    user_message=request.text,
    context={
        "user_id": user_id, 
        "key_id": request.key_id,
        "model_preference": model,  # Теперь передаётся модель
    },
    api_key=api_key,
    provider=provider
)
logger.info(f"Pipeline result: provider={result.provider}, success={result.success}")
```

### 3. `backend/api/frontend_routes.py` — `chat/stream` endpoint

Аналогичные улучшения логирования для streaming чата.

## Ожидаемое поведение после исправления

### Успешный сценарий (OpenRouter)
```
Chat request: key_id=abc123, model=auto, provider=None
Looking up key_id: abc123 for user xyz789
✅ Key found: provider=openrouter, meta-llama/llama-3.1-8b-instruct:free
✅ Key decrypted, length=32
✅ Using: provider=openrouter, model=meta-llama/llama-3.1-8b-instruct:free, key_length=32
GeneratePhase: api_key=***, provider=openrouter
GeneratePhase: calling ProviderManager with provider=openrouter, model=meta-llama/llama-3.1-8b-instruct:free
GeneratePhase: success - provider=openrouter, fallback_used=False
Pipeline result: provider=openrouter, success=True
```

### Fallback сценарий (OpenRouter → GigaChat)
```
GeneratePhase: calling ProviderManager with provider=openrouter, model=...
⚠️ Provider openrouter failed: 401 Unauthorized
GeneratePhase: success - provider=gigachat, fallback_used=True
Pipeline result: provider=gigachat, success=True
```

### Ошибка (нет ключа)
```
❌ No API key available for user xyz789
HTTPException: API ключ не настроен. Добавьте ключ в настройках.
```

## Как проверить

### 1. Проверка логов
```bash
# Запустите backend
cd backend && python main.py

# В другом терминале отправьте запрос
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Привет!", "key_id": "YOUR_KEY_ID"}'
```

### 2. Ожидаемые логи
```
✅ Key found: provider=openrouter, model=...
✅ Key decrypted, length=32
✅ Using: provider=openrouter, model=..., key_length=32
GeneratePhase: api_key=***, provider=openrouter
GeneratePhase: success - provider=openrouter, fallback_used=False
```

### 3. Проверка fallback
- Отключите интернет или используйте невалидный ключ OpenRouter
- Должен сработать fallback на GigaChat (если настроен системный ключ)

## Дальнейшие шаги

### Фаза 2: Проверка RLS политик (если проблема сохранится)

1. **Проверить RLS политики в Supabase:**
```sql
-- Подключитесь к Supabase SQL Editor
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- Проверить политику для user_api_keys
SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'user_api_keys';
```

2. **Применить исправления из `APPLY_RLS_FIX.md`**

3. **Запустить скрипты диагностики:**
```bash
python scripts/check_rls_policies.py
python scripts/check_tables.py
python scripts/check_with_service.py
```

## Файлы изменённые

- `backend/core/pipeline/phases/generate.py` — упрощена логика, добавлено логирование
- `backend/api/frontend_routes.py` — улучшено логирование в `chat` и `chat/stream`
- `docs/RLS_PROVIDERS_FIX_2026_06_10.md` — этот документ

## Примечания

- **LiteLLM не удалён** — остаётся как legacy, но не используется в основном flow
- **RLS политики** — исправления применяются только если проблема сохранится после этого фикса
- **Fallback** — теперь работает автоматически через `ProviderManager`
