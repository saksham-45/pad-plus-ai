# 🚀 Руководство по установке PAD+ AI

## Требования

- **Python 3.10+** (рекомендуется 3.14)
- **Node.js 16+** и npm
- **Аккаунт Supabase** (бесплатно): https://supabase.com
- **API ключ провайдера LLM** (один из):
  - GigaChat: https://developers.sber.ru/gigachat
  - Groq: https://console.groq.com
  - OpenAI: https://platform.openai.com
  - Или другой через LiteLLM

---

## 1. Клонирование

```bash
git clone https://github.com/your-username/padplus-ai.git
cd padplus-ai
```

---

## 2. Настройка базы данных (Supabase)

### 2.1. Создайте проект на Supabase

1. Зайдите на https://supabase.com
2. Создайте новый проект
3. Скопируйте:
   - **Project URL** (вида `https://xxxxx.supabase.co`)
   - **anon/public key** (начинается с `sb_publishable_`)
   - **service_role key** (начинается с `sb_secret_`)

### 2.2. Создайте таблицы

В Supabase Dashboard → SQL Editor выполните миграции из `backend/database/migrations/`:

1. `001_initial_schema.sql` — создание таблиц
2. `002_rls_policies.sql` — политики безопасности
3. `003_fix_rls_policies.sql` — исправление политик

---

## 3. Настройка backend

### 3.1. Установка зависимостей

```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 3.2. Конфигурация .env

Скопируйте пример и заполните:

```bash
cp .env.example .env
```

Обязательные поля:

```env
# Supabase
SUPABASE_URL=https://ваш-проект.supabase.co
SUPABASE_KEY=sb_publishable_...
SUPABASE_SERVICE_KEY=sb_secret_...

# Шифрование (сгенерируйте один раз!)
ENCRYPTION_KEY=<сгенерируйте>
ENCRYPTION_SALT=<сгенерируйте>
```

Генерация ключей шифрования:

```bash
# ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ENCRYPTION_SALT
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

⚠️ **Сохраните эти значения!** При потере все зашифрованные ключи станут нечитаемыми.

### 3.3. GigaChat (опционально)

Для GigaChat добавьте в `.env`:

```env
GIGACHAT_AUTH_KEY=ваш_authorization_key_из_консоли
```

Получить ключ: https://developers.sber.ru/gigachat → Кабинет разработчика → Авторизационные данные

---

## 4. Настройка frontend

```bash
cd frontend
npm install
cd ..
```

---

## 5. Запуск

### Вариант 1: Автоматический (Windows)

```bash
start.bat
```

### Вариант 2: Вручную (две консоли)

**Консоль 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

**Консоль 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### 6. Откройте приложение

http://localhost:5174

---

## 7. Первый запуск

1. **Зарегистрируйтесь** через форму входа
2. **Добавьте API ключ провайдера:**
   - Перейдите на страницу **⚡ Провайдеры**
   - Нажмите **Connect** у нужного провайдера
   - Введите API ключ
   - Отметьте «Использовать по умолчанию»
3. **Начните чат** — перейдите на вкладку **💬 Чат**

---

## Поддерживаемые провайдеры

| Провайдер | Тип | Бесплатно |
|-----------|-----|-----------|
| GigaChat | OAuth | ✅ Да (с лимитами) |
| Groq | API Key | ✅ Да (с лимитами) |
| OpenAI | API Key | ❌ Платный |
| Google Gemini | API Key | ✅ Да (с лимитами) |
| Anthropic Claude | API Key | ❌ Платный |
| OpenRouter | API Key | ✅ Есть бесплатные модели |

---

## Устранение проблем

### Сервер не запускается

```bash
# Проверьте .env
cat .env

# Проверьте подключение к Supabase
python -c "from core.supabase_client import get_supabase; print(get_supabase())"
```

### Ошибка шифрования

Убедитесь что `ENCRYPTION_KEY` и `ENCRYPTION_SALT` заданы в `.env` и не менялись после первого запуска.

### GigaChat не подключается

- Убедитесь что `GIGACHAT_AUTH_KEY` — это **authorization key** (base64), а не client_id
- Ключ должен быть в формате: `client_id:client_secret` закодированный в base64

### Frontend не видит backend

Проверьте что backend запущен на `http://127.0.0.1:8080` и CORS настроен для `http://localhost:5174`.
