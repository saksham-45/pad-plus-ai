# Диагностика проблем с GigaChat: Почему раньше работало, а теперь нет

## Возможные причины изменения состояния

### 1. Изменились API-ключи или срок их действия

#### Проверьте:
- Не истёк ли срок действия ваших API-ключей GigaChat
- Не изменился ли формат AUTHORIZATION_KEY
- Не было ли ограничений на количество запросов

#### Что делать:
- Перегенерируйте API-ключи на developers.sber.ru
- Проверьте статус своего аккаунта в системе GigaChat API

### 2. Изменилась конфигурация проекта

#### Проверьте изменения в:
- `backend/llm/gigachat.py` - изменился ли способ загрузки переменных
- `backend/main.py` - изменился ли порядок инициализации
- `requirements.txt` - обновились ли зависимости
- `.env` файл - изменились ли значения переменных

### 3. Изменилась версия зависимостей

#### Проверьте:
- Версии библиотек в `requirements.txt`
- Совместимость с новыми версиями `httpx`, `python-dotenv`, `fastapi`

### 4. Изменились системные настройки

#### Проверьте:
- Не изменился ли путь к проекту
- Не изменились ли права доступа к файлам
- Не обновилась ли операционная система
- Не изменились ли настройки антивируса (он может блокировать сетевые запросы)

### 5. Проблемы с сетью или доступностью API

#### Проверьте:
- Доступны ли эндпоинты GigaChat:
  - `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
  - `https://gigachat.devices.sberbank.ru/api/v1/chat/completions`
- Не изменилась ли политика брандмауэра
- Не блокирует ли антивирус соединения

### 6. Изменилось поведение uvicorn или Python

#### Проверьте:
- Не обновился ли Python
- Не изменилось ли поведение uvicorn при загрузке переменных окружения
- Правильно ли загружается .env файл при запуске

## Проверка пошагово

### 1. Проверка .env файла
```bash
# Убедитесь, что файл .env находится в корне проекта
dir .env

# Проверьте содержимое
type .env
```

### 2. Проверка загрузки переменных в Python
Создайте временный скрипт `test_env.py`:
```python
from pathlib import Path
from dotenv import load_dotenv
import os

# Загружаем .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=== Загрузка переменных окружения ===")
print(f"GIGACHAT_CLIENT_ID: {bool(os.getenv('GIGACHAT_CLIENT_ID'))}")
print(f"GIGACHAT_AUTHORIZATION_KEY: {bool(os.getenv('GIGACHAT_AUTHORIZATION_KEY'))}")
print(f"GIGACHAT_SCOPE: {os.getenv('GIGACHAT_SCOPE')}")
print(f"GIGACHAT_ENABLED: {os.getenv('GIGACHAT_ENABLED')}")

print("\n=== Проверка GigaChat клиента ===")
try:
    from backend.llm.gigachat import gigachat
    print(f"GigaChat enabled: {gigachat.enabled}")
    print(f"GigaChat token: {gigachat.token is not None}")
except Exception as e:
    print(f"Ошибка при загрузке GigaChat: {e}")
```

Запустите:
```bash
python test_env.py
```

### 3. Проверка соединения вручную
```python
import httpx
import base64

# Ваши данные из .env
auth_key = os.getenv('GIGACHAT_AUTHORIZATION_KEY')
client_id = os.getenv('GIGACHAT_CLIENT_ID')
scope = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Authorization": f"Basic {auth_key}",
}

payload = f"scope={scope}"

print("=== Проверка запроса токена ===")
try:
    import uuid
    rquid = str(uuid.uuid4())
    headers["RqUID"] = rquid
    
    response = httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers=headers,
        data=payload,
        verify=False
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Ошибка соединения: {e}")
```

### 4. Проверка логов при запуске
Запустите сервер и внимательно посмотрите логи:
- Есть ли сообщения о загрузке .env файла
- Есть ли сообщения об ошибке при инициализации GigaChat
- Есть ли сетевые ошибки

### 5. Проверка через API
После запуска сервера:
```
GET http://localhost:8000/api/v1/gigachat/status
```

## Возможные изменения в проекте

### Проверьте, не изменились ли:
- Структура проекта
- Пути к файлам
- Версии библиотек
- Настройки CORS
- Порядок инициализации компонентов

### Сравните с рабочей версией:
- Если у вас есть git, проверьте последние изменения:
```bash
git log --oneline -10
git diff HEAD~1 HEAD
```

## Решения

### 1. Восстановление рабочей конфигурации
Если у вас есть резервная копия рабочего состояния, сравните файлы:
- `.env`
- `requirements.txt`
- `backend/llm/gigachat.py`
- `backend/main.py`

### 2. Проверка на чистой установке
Создайте копию проекта в новой директории и проверьте, работает ли там.

### 3. Временное отключение других провайдеров
Временно отключите другие провайдеры, чтобы точно знать, что используется именно GigaChat.

## Важные замечания

### Если раньше работало, возможно:
- Изменились ключи на стороне GigaChat API
- Изменились требования к формату ключей
- Изменились сетевые политики
- Было обновление системы, затронувшее работу с сетевыми запросами

### Рекомендации:
- Сохраните рабочую конфигурацию в отдельной ветке или коммите
- Делайте резервные копии перед крупными изменениями
- Ведите журнал изменений, чтобы легче отслеживать, что могло повлиять на работоспособность