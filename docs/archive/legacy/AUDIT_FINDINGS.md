# Audit Findings Report

Дата: 28 мая 2026 г.
Проект: PAD+ AI чистый

## 1. Краткое резюме

Аудит выявил критические и высокие риски в следующих областях:
- утечки секретов и конфигураций в репозитории
- отключённая проверка TLS (`verify=False`) при вызовах внешних API
- неаутентифицированный WebSocket endpoint
- небезопасные CORS/CSRF настройки в production-конфигурации
- хранение в памяти rate limit состояния
- неявные fallback-логики Supabase service role / anon key
- риск логирования чувствительной информации

## 2. Основные находки

| Файл | Строка | Категория | Уровень | Проблема | Рекомендация |
|---|---|---|---|---|---|
| `.env` | 10, 13, 16-17, 21, 50-52 | Секреты в репозитории | Критично | Хранение секретов и ключей доступа в коммитнутом `.env` | Удалить файл из репозитория, добавить в `.gitignore`, ротировать ключи |
| `backend/.env` | 12-14, 20 | Секреты в репозитории | Критично | Хранение Publishable и Service Role ключей Supabase в `backend/.env` | Удалить и использовать безопасное хранилище секретов |
| `render.yaml` | 30 | Секреты в инфраструктуре | Критично | Открытая строка `SUPABASE_KEY` в конфигурации Render | Заменить на переменную окружения Render Secret |
| `backend/runtime/litellm_service.py` | 91, 368, 398 | TLS / сеть | Критично | `verify=False` отключает проверку сертификатов | Включить проверку TLS и удалить `verify=False` |
| `backend/main.py` | 218-219, 281 | CSRF/CORS | Высокий | `cookie_secure=False` и разрешение `allow_origins=["*"]` создают серьёзный риск для production | Установить `cookie_secure=True`, ограничить CORS конкретными доменами |
| `backend/main.py` | 375-379 | WebSocket | Высокий | WebSocket endpoint `/ws` не проверяет аутентификацию перед `accept()` | Добавить проверку токена/сессии до `accept()` |
| `backend/security_middleware.py` | 33, 93-99, 109 | Rate limiting | Средний | Хранение состояния rate limit в памяти делает защиту бесполезной при нескольких инстансах | Использовать внешний кеш/Redis или API Gateway rate limiting |
| `backend/core/supabase_client.py` | 70-89, 134-145 | Supabase конфигурация | Средний | Непрозрачный fallback на `SUPABASE_SERVICE_KEY` / `SUPABASE_KEY` может привести к случайному использованию service role ключа | Сделать поведение явным, запретить service role key в публичных окружениях |
| `backend/api/frontend_routes.py` | 309 | RLS bypass | Средний | Комментарий указывает на вставку данных через service role для обхода RLS | Проверить безопасность RLS и убрать неявные bypass-пути |
| `backend/api/document_routes.py` | 153 | RLS bypass | Средний | Метаданные сохраняются через service role, обходя RLS | Пересмотреть модель данных и минимизировать использование service role |
| `backend/api/frontend_routes.py` | 602 | Логирование | Низкий | Логируются размер и начало raw API ключа при создании ключа | Убрать логирование, сохранять минимум метаданных |

## 3. Детальные находки

### 3.1 Секреты и конфигурации
- `.env` содержит реальные значения `DATABASE_URL`, `ENCRYPTION_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `ADMIN_MASTER_KEY`, `CSRF_SECRET_KEY`, `REDIS_URL`.
- `backend/.env` также содержит `SUPABASE_SERVICE_KEY` и `ENCRYPTION_KEY`.
- `render.yaml` явно содержит `SUPABASE_KEY` на строке 30.

### 3.2 Сетевые и TLS настройки
- `backend/runtime/litellm_service.py`, строки 91, 368, 398: `verify=False` в `httpx.AsyncClient` и `requests` отключает проверку сертификатов, что делает соединение уязвимым для MITM.

### 3.3 WebSocket и аутентификация
- `backend/main.py`, строки 375-379: endpoint `@app.websocket("/ws")` принимает подключение без проверки авторизации.

### 3.4 CSRF и CORS
- `backend/main.py`, строки 218-219: `cookie_secure=False` используется даже в одном `production`-комментарии, что опасно для реального HTTPS.
- `backend/main.py`, строка 281: `allow_origins=["*"]` разрешает любые источники, что увеличивает риск CSRF/CSR.

### 3.5 Rate limiting
- `backend/security_middleware.py`, строки 33, 93-99, 109: состояние rate limit хранится в памяти, не работает для распределённого развертывания.

### 3.6 Supabase / RLS
- `backend/core/supabase_client.py`, строки 70-89 и 134-145: код допускает несколько путей и fallback-логик подключения Supabase, что усложняет безопасность.
- `backend/api/frontend_routes.py`, строка 309: комментарий допускает обход RLS через service role.
- `backend/api/document_routes.py`, строка 153: service role используется для сохранения метаданных.

### 3.7 Логирование
- `backend/api/frontend_routes.py`, строка 602: логируются длина raw API ключа и первые символы, что является избыточным.

## 4. Рекомендации
1. Удалить `.env`, `backend/.env`, и любые файлы с ключами из репозитория; добавить их в `.gitignore`.
2. Ротировать все Supabase ключи, Redis ключи и шифровальные ключи.
3. В `backend/runtime/litellm_service.py` включить TLS везде: убрать `verify=False`.
4. В `backend/main.py` сделать `cookie_secure=True` и ограничить `allow_origins` списком доверенных доменов.
5. Защитить WebSocket endpoint `/ws` проверкой авторизации до `await websocket.accept()`.
6. Перенести rate limit в Redis или внешнее хранилище, если есть несколько реплик приложения.
7. Упростить Supabase init: явное разделение `anon` и `service_role`, запретить service role key для публичного backend.
8. Удалить логирование raw API ключей и любых метаданных ключей.
9. Проверить RLS-механизмы и убрать бэкенд-пути обхода RLS, если возможно.
10. Добавить сканирование на секреты в CI и запрет коммита ключей в репозиторий.

## 5. Последующие шаги
- Выполнить ревью истории git на предмет утекших ключей.
- Настроить безопасное хранилище секретов (Vault, Render Secrets, GitHub Secrets и т.д.).
- Провести повторный аудит после устранения критических замечаний.
