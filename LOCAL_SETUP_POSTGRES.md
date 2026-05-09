# 🚀 Локальный запуск PAD+ AI ([PostgreSQL](.) версия)

## 📋 Что изменилось

- ❌ **Удалён ChromaDB** — больше не требует 300-400MB RAM
- ✅ **Используется PostgreSQL + pgvector** — экономит память
- ✅ **Только Supabase/PostgreSQL** — как на production

---

## 🛠️ Установка

### Шаг 1: Проверь .env

В файле `.env` должна быть переменная:

```env
DATABASE_URL=postgresql://postgres.hgjbjccpeirwrabbcjhr:TiMuPom13Q5OfKBi@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
```

### Шаг 2: Инициализируй базу данных

Открой **Supabase SQL Editor** (https://supabase.com/dashboard) и выполни:

```sql
-- 1. Включить pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Создать таблицу
CREATE TABLE IF NOT EXISTS rag_dialogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    summary TEXT,
    keywords TEXT[],
    topic TEXT DEFAULT 'общее',
    topic_confidence FLOAT DEFAULT 0.5,
    sentiment TEXT DEFAULT 'neutral',
    entities JSONB DEFAULT '[]',
    relations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Индексы
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_user_id ON rag_dialogs(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_topic ON rag_dialogs(topic);
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_created_at ON rag_dialogs(created_at DESC);
```

Или запусти файл `scripts/init_rag_postgres.sql`

### Шаг 3: Установи зависимости

```powershell
pip install psycopg2-binary
```

### Шаг 4: Запусти бэкенд

```powershell
python backend/main.py
```

Ожидаемый вывод:
```
✅ PostgreSQL доступен
📁 Инициализация RAG Memory v3.0 (PostgreSQL)
✅ RAG Memory PostgreSQL инициализирован
🚀 Starting server on port 8080
```

### Шаг 5: Запусти фронтенд (в другом терминале)

```powershell
cd frontend
npm run dev
```

---

## ✅ Проверка

### 1. Проверь что PostgreSQL работает

```powershell
python -c "import psycopg2; print('✅ psycopg2 установлен')"
```

### 2. Проверь подключение к базе

```powershell
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('DATABASE_URL:', os.getenv('DATABASE_URL')[:50] + '...')"
```

### 3. Открой в браузере

- Frontend: http://localhost:5174
- Backend health: http://localhost:8080/health

---

## 🐛 Устранение проблем

### Ошибка: "PostgreSQL не доступен"

**Решение:**
```powershell
pip install psycopg2-binary
```

### Ошибка: "DATABASE_URL не настроен"

**Решение:** Добавь в `.env`:
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### Ошибка: "pgvector расширение не найдено"

**Решение:** Выполни в Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Ошибка: "Chromadb not found"

**Решение:** Это значит старый код ещё в памяти. Перезапусти Python полностью.

---

## 📊 Преимущества

| Было (ChromaDB) | Стало (PostgreSQL) |
|----------------|-------------------|
| ~300-400MB RAM | ~20MB RAM |
| 1GB диск | 0MB диск |
| Медленный старт | Быстрый старт |
| Требует отдельного сервиса | Использует ту же БД |

---

## 🎯 Что дальше?

1. Запусти приложение
2. Протестируй чат
3. Проверь X-Ray панель
4. Убедись что память работает

**Готово! 🎉**