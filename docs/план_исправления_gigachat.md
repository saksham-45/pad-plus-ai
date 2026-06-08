# План исправления GigaChat

## Проблемы в `_generate_gigachat` (backend/runtime/llm_service.py)

1. **Двойное создание httpx клиента** — создаётся клиент для auth, потом другой для chat
2. **Base64 логика сломана** — непонятное условие `len(secret) > 80`
3. **Auth URL использует devices.sberbank.ru** — правильный URL: `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
4. **Timeout 10с для auth** — может быть мало
5. **Нет повторных попыток** при временных ошибках сети
6. **Нет подробного логирования** каждого шага

## План действий

### Шаг 1: Исправить `_generate_gigachat` 
- Использовать единый `self._session` (как в `_generate_openrouter`)
- Исправить логику обработки ключа
- Добавить подробное логирование каждого шага
- Добавить retry при временных ошибках
- Увеличить timeout

### Шаг 2: Добавить debug endpoint
- `GET /api/v1/debug/gigachat` — тестирует весь flow
- Проверяет: чтение ключа из БД → расшифровка → auth → chat

### Шаг 3: Исправить streaming для GigaChat
- `generate_stream` сейчас не стримит — только yield response.text
- Нужно сделать настоящий SSE streaming

### Шаг 4: Добавить test-connection для GigaChat
- Эндпоинт тестирования ключа GigaChat с понятными ошибками