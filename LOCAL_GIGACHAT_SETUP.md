# Настройка GigaChat для локального запуска

## Проверка локальной конфигурации

### 1. Проверьте файл .env

Убедитесь, что в корне проекта (в директории `padplus-ai`) у вас есть файл `.env` со следующими настройками:

```env
# GigaChat API Configuration
GIGACHAT_CLIENT_ID=ваш_client_id
GIGACHAT_AUTHORIZATION_KEY=ваш_base64_закодированный_authorization_key
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_ENABLED=true

# Другие настройки
DEBUG=true
LANGUAGE=ru
```

### 2. Проверьте правильность AUTHORIZATION_KEY

AUTHORIZATION_KEY должен быть Base64-кодированным значением в формате `client_id:client_secret`. Проверьте, что вы сгенерировали его правильно:

```bash
echo -n "ваш_client_id:ваш_client_secret" | base64
```

Пример корректного значения:
```
GIGACHAT_AUTHORIZATION_KEY=OTkyNTczMWUtMTI2Ny00ZTJjLTg1NTItNjVlOGYwOTYxMGExOmYzYzE2ZjUwLThjYmItNDQxZi04MjEwLTc3ZThkYzcyY2NlMA==
```

## Запуск локального сервера

### 1. Убедитесь, что вы в правильной директории

Перейдите в корневую директорию проекта:

```bash
cd c:/Users/1/OneDrive/Desktop/padplus-ai
```

### 2. Установите зависимости

```bash
cd backend
pip install -r ../requirements.txt
```

### 3. Запустите сервер

```bash
python -m uvicorn main:app --reload --port 8000
```

ИЛИ

```bash
cd ..
python -m backend.main
```

## Проверка работы GigaChat

### 1. Проверьте статус GigaChat

Откройте в браузере:
```
http://localhost:8000/api/v1/gigachat/status
```

Должен вернуться ответ типа:
```json
{
  "enabled": true,
  "has_token": false,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 2. Протестируйте подключение

```
http://localhost:8000/api/v1/gigachat/test
```

### 3. Используйте API для генерации

```bash
curl -X POST http://localhost:8000/api/v1/gigachat/raw \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Привет, как дела?", "context": ""}'
```

## Решение распространенных проблем

### 1. Переменные окружения не загружаются

Если GigaChat отображается как отключенный, проверьте:

1. **Расположение файла .env** - он должен быть в корне проекта
2. **Загрузка переменных** - в файле `backend/llm/gigachat.py` есть строка:
   ```python
   from dotenv import load_dotenv
   env_path = Path(__file__).parent.parent.parent / ".env"
   load_dotenv(env_path)
   ```

### 2. Ошибка авторизации

Если получаете ошибку 401 Unauthorized:
1. Проверьте, что AUTHORIZATION_KEY сгенерирован правильно
2. Убедитесь, что CLIENT_ID и AUTHORIZATION_KEY действительны
3. Проверьте, что у вас есть доступ к GigaChat API

### 3. SSL-ошибки

В коде используется `verify=False` для httpx клиентов, что позволяет работать с сертификатами Sber устройств.

### 4. Проверка через Python

Вы можете проверить, правильно ли загружаются переменные:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

print("GIGACHAT_CLIENT_ID:", os.getenv("GIGACHAT_CLIENT_ID"))
print("GIGACHAT_AUTHORIZATION_KEY:", os.getenv("GIGACHAT_AUTHORIZATION_KEY"))
print("GIGACHAT_ENABLED:", os.getenv("GIGACHAT_ENABLED"))
```

## Использование с сессиями

Если вы хотите использовать GigaChat с конкретной сессией:

```bash
curl -X POST http://localhost:8000/api/v1/llm/config \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: ваш_session_id" \
  -d '{
    "gigachat": {
      "enabled": true,
      "api_key": "ваш_authorization_key"
    },
    "gemini": {
      "enabled": false,
      "api_key": null
    },
    "openrouter": {
      "enabled": false,
      "api_key": null,
      "model": "google/gemma-7b-it"
    }
  }'
```

## Запуск с отладкой

Для отладки запустите сервер с включенным DEBUG:

```bash
DEBUG=true python -m uvicorn main:app --reload --port 8000
```

Или установите `DEBUG=true` в файле `.env`.

## Проверка логов

При запуске сервера обращайте внимание на логи, особенно на сообщения:
- `✅ GigaChat не настроен. Укажите ключ в .env файле.` - означает, что переменные не загружены
- `🔐 Запрашиваем новый Access Token у GigaChat...` - означает, что система пытается подключиться
- `✅ Новый Access Token получен` - означает успешное подключение

## Перезапуск сервера

После внесения изменений в файл `.env`, обязательно перезапустите сервер, чтобы переменные окружения были перезагружены.