# ⚡ БЫСТРАЯ ИНСТРУКЦИЯ - КРИТИЧЕСКИЕ ШАГИ (СКОПИРУЙ-ВСТАВЬ)

**Читай этот файл для пошагового выполнения критических действий.**

---

## 🔑 ШАГ 1: СГЕНЕРИРОВАТЬ НОВЫЕ КЛЮЧИ (5 мин)

Откройте PowerShell/Terminal и выполните эти команды:

### Генерируем ENCRYPTION_KEY
```bash
python -c "import base64, os; print('ENCRYPTION_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
**Скопируйте вывод в текстовый файл** (будет нужен позже)

### Генерируем ENCRYPTION_SALT
```bash
python -c "import base64, os; print('ENCRYPTION_SALT=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
**Скопируйте вывод в текстовый файл**

### Генерируем CSRF_SECRET_KEY
```bash
python -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))"
```
**Скопируйте вывод в текстовый файл**

**Результат должен быть такой:**
```
ENCRYPTION_KEY=abc123xyz...==
ENCRYPTION_SALT=def456uvw...==
CSRF_SECRET_KEY=ghi789rst...
```

---

## 🔄 ШАГ 2: РОТИРОВАТЬ КЛЮЧИ В SUPABASE (10 мин)

### 2.1 Создать новый Supabase API Key

1. Откройте https://app.supabase.com
2. Выберите ваш проект (PAD+ AI)
3. Settings (левое меню) → API
4. Нажмите "Generate New Publishable Key"
5. Копируйте новое значение: `sb_publishable_xxxxx`
   
**Это будет ваш новый `SUPABASE_KEY`**

### 2.2 Изменить пароль PostgreSQL

1. Settings (левое меню) → Database
2. Найдите секцию "Password"
3. Нажмите "Change password"
4. Установите новый пароль (16+ символов, с большими буквами и цифрами)
5. Скопируйте новый `DATABASE_URL` (выглядит так):
   ```
   postgresql://postgres.xxxxx:NEW_PASSWORD@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
   ```

**Это будет ваш новый `DATABASE_URL`**

---

## 🗑️ ШАГ 3: УДАЛИТЬ .env ИЗ GIT (15 мин)

### 3.1 Установить BFG (если не установлен)

**Windows (с Chocolatey):**
```bash
choco install bfg
```

**Без Chocolatey:**
1. Скачайте https://rtyley.github.io/bfg-repo-cleaner/
2. Распакуйте в `C:\bfg\` или подобное место
3. Добавьте в PATH или используйте полный путь

### 3.2 Выполнить BFG команды

```bash
# 1. Перейдите в корень проекта
cd C:\пад\ ал\ датабаз а\ чистый\PAD+\ AI\ чистый

# 2. Убедитесь что все committed
git status
# Должно быть: "nothing to commit, working tree clean"

# 3. Запустите BFG (удаляет .env из истории)
bfg --delete-files .env

# 4. Очистите рефлоги
git reflog expire --expire=now --all

# 5. Очистите garbage
git gc --prune=now --aggressive

# 6. Проверьте что .env удален из истории
git log --all --full-history -- .env
# Должно быть сообщение: fatal: your current branch appears to be empty
```

### 3.3 Push в GitHub (ПЕРЕПИСЫВАЕТ ИСТОРИЮ!)

```bash
# ⚠️ Это переписывает историю репозитория!
# Все остальные ветки должны быть rebased после этого.

git push --force-with-lease origin main
# или
git push --force-with-lease origin master
```

**После этого все должны обновить свои локальные копии:**
```bash
# На других машинах:
git pull --rebase origin main
# или
git clone https://github.com/your-username/pad-plus-ai.git  # новая копия
```

---

## 🚀 ШАГ 4: РАЗВЕРНУТЬ НА RENDER (20 мин)

### 4.1 Перейти на Render.com

Откройте https://render.com и войдите с GitHub

### 4.2 Создать Web Service

1. New → Web Service
2. Connect a repository → Choose "pad-plus-ai" (GitHub)
3. Нажмите Connect
4. Заполните форму:
   - Name: `pad-plus-ai-backend`
   - Plan: **Free** ← ВАЖНО!
   - Runtime: Python
   - Build Command: *(возьмется из render.yaml)*
   - Start Command: *(возьмется из render.yaml)*
5. Нажмите Create Web Service

### 4.3 Установить Environment Variables

1. Перейдите в Services → pad-plus-ai-backend
2. Settings → Environment Variables
3. **Добавьте эти переменные (скопируйте-вставьте):**

```
DATABASE_URL = postgresql://postgres.xxxxx:NEW_PASSWORD@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
SUPABASE_URL = https://your-project.supabase.co
SUPABASE_KEY = sb_publishable_xxxxx
ENCRYPTION_KEY = (из шага 1)
ENCRYPTION_SALT = (из шага 1)
CSRF_SECRET_KEY = (из шага 1)
FRONTEND_URL = https://your-frontend.onrender.com
REDIS_URL = rediss://default:password@host.upstash.io:6379
```

### 4.4 Deploy

1. Нажмите Manual Deploy → Deploy latest commit
2. Ждите (5-15 минут)
3. Смотрите логи: Logs tab

---

## ✅ ПРОВЕРКА ПОСЛЕ ДЕПЛОЯ (5 мин)

### Проверка 1: Health Status

```bash
# Замените на ваш URL (берется из Render Dashboard)
curl https://pad-plus-ai-backend.onrender.com/health

# Ответ должен быть:
# {"status":"healthy","version":"4.0.0","database":"connected","cache":"connected"}
```

### Проверка 2: HTTPS работает

```bash
curl -I https://pad-plus-ai-backend.onrender.com/health
# HTTP/2 200
```

### Проверка 3: Логи не содержат ошибок

1. На Render Dashboard перейдите в Logs
2. Ищите строки:
   - ✅ "ANTI_DIRECTIVE проверена"
   - ✅ "Cache manager инициализирован"
   - ✅ "PAD+ AI готов к работе"
3. ❌ Не должно быть: "Error", "Failed", "Exception"

---

## 🚨 ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК

### Если Build Timeout

1. Нажмите "Manual Deploy" еще раз
2. Если снова timeout - проверьте логи Build
3. Может быть: npm install слишком долгий

### Если Health Check Failed

1. Проверьте что SUPABASE_KEY правильный
2. Проверьте что DATABASE_URL правильный
3. Проверьте логи на "connection error"

### Если CORS Error

1. Убедитесь что FRONTEND_URL установлен
2. FRONTEND_URL должен быть точный домен (не localhost!)
3. Пример: `https://pad-plus-ai-frontend.onrender.com`

### Если "Permission denied" при push

```bash
# Может быть нужно переавторизоваться в GitHub
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
git config --global credential.helper store
# Повторите git push
```

---

## ✨ ВСЕ ГОТОВО!

После выполнения этих шагов ваше приложение будет:

✅ Безопасно (ключи скрыты, middleware включены)  
✅ Развернуто на Render (free tier)  
✅ Доступно по HTTPS  
✅ Защищено от DoS и CSRF  
✅ С валидацией файлов  

---

## 📋 ЧЕКЛИСТ

```
Шаг 1: Сгенерировать ключи
☐ ENCRYPTION_KEY сгенерирован
☐ ENCRYPTION_SALT сгенерирован
☐ CSRF_SECRET_KEY сгенерирован

Шаг 2: Ротировать в Supabase
☐ Новый SUPABASE_KEY создан
☐ Новый DATABASE_URL создан
☐ Старые ключи заменены

Шаг 3: Удалить из git
☐ BFG установлен
☐ BFG команды выполнены
☐ git push --force-with-lease сделан

Шаг 4: Развернуть на Render
☐ Web Service создан
☐ Environment Variables установлены
☐ Deploy запущен
☐ Health check проходит

Шаг 5: Финальная проверка
☐ curl /health возвращает healthy
☐ HTTPS работает
☐ Логи без ошибок
```

---

**Время выполнения:** ~50 минут  
**Сложность:** Средняя  
**Риск:** Минимальный (все команды приведены, инструкции подробные)

После этого PAD+ AI будет полностью развернут и защищен! 🎉
