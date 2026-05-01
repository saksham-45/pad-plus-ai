# Исправление запуска GigaChat через start.bat

## Проблема

При запуске через `start.bat` система может не загружать переменные окружения из файла `.env`, что приводит к отключению GigaChat, даже если он настроен в файле.

## Причины проблемы

1. **Uvicorn не загружает .env файлы автоматически** - uvicorn запускает приложение в отдельном процессе
2. **Путь к .env файлу** - возможно, в коде указан неправильный путь к .env файлу
3. **Порядок загрузки** - переменные могут загружаться после инициализации GigaChat клиента

## Решение

### 1. Проверьте путь к .env файлу в коде

В файле `backend/llm/gigachat.py` убедитесь, что строка загрузки .env указывает на правильный путь:

```python
# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
```

### 2. Альтернативное решение: экспорт переменных в bat-файле

Можно модифицировать команду запуска в `start.bat`, чтобы экспортировать переменные перед запуском:

```
start "PAD+ Backend" cmd /k "cd /d "%~dp0" && set /p GIGACHAT_CLIENT_ID=<.env && set /p GIGACHAT_AUTHORIZATION_KEY=<.env && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
```

Но лучше использовать другой подход - создать скрипт, который загрузит переменные и запустит сервер.

### 3. Проверка загрузки переменных

Для проверки, действительно ли переменные загружаются, можно добавить отладочный вывод в файл `backend/llm/gigachat.py`:

```python
import os
import logging

logger = logging.getLogger("neuromind.gigachat")

# После загрузки .env
logger.info(f"GIGACHAT_CLIENT_ID loaded: {bool(os.getenv('GIGACHAT_CLIENT_ID'))}")
logger.info(f"GIGACHAT_AUTHORIZATION_KEY loaded: {bool(os.getenv('GIGACHAT_AUTHORIZATION_KEY'))}")
logger.info(f"GIGACHAT_ENABLED: {os.getenv('GIGACHAT_ENABLED')}")
```

### 4. Альтернативный способ запуска

Вместо использования uvicorn напрямую, можно создать специальный запуск, который гарантирует загрузку переменных:

Создайте в корне проекта файл `run_backend.py`:

```python
"""
Специальный скрипт для запуска backend с правильной загрузкой .env
"""
import sys
import os
from pathlib import Path

# Загружаем .env файл перед импортом других модулей
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Проверяем загрузку переменных
print("Загруженные переменные:")
print(f"GIGACHAT_CLIENT_ID: {'✓' if os.getenv('GIGACHAT_CLIENT_ID') else '✗'}")
print(f"GIGACHAT_AUTHORIZATION_KEY: {'✓' if os.getenv('GIGACHAT_AUTHORIZATION_KEY') else '✗'}")
print(f"GIGACHAT_ENABLED: {os.getenv('GIGACHAT_ENABLED')}")

# Теперь импортируем и запускаем основное приложение
from backend.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "run_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

### 5. Использование python-dotenv в uvicorn

Другой способ - использовать python-dotenv при запуске uvicorn:

Измените команду в `start.bat` на:

```
start "PAD+ Backend" cmd /k "cd /d "%~dp0" && python -c "from dotenv import load_dotenv; load_dotenv(); import uvicorn; from backend.main import app; uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)""
```

### 6. Проверка после запуска

После запуска через `start.bat`:

1. Откройте браузер и перейдите на `http://localhost:8000/api/v1/gigachat/status`
2. Проверьте, что `enabled` равно `true`
3. Протестируйте подключение через `http://localhost:8000/api/v1/gigachat/test`

### 7. Проверка логов

В консоли backend-сервиса должны появиться сообщения:
- `✅ GigaChat не настроен. Укажите ключ в .env файле.` - если переменные не загружены
- `🔐 Запрашиваем новый Access Token у GigaChat...` - если переменные загружены и система пытается подключиться

## Рекомендуемое решение

Наиболее надежный способ - использовать специальный запускающий скрипт, как описано в пункте 4. Это гарантирует, что переменные окружения будут загружены до инициализации любых компонентов системы.