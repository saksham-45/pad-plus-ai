# ИНСТРУКЦИЯ ПО РАЗВЕРТЫВАНИЮ PAD+ AI НА RENDER (БЕСПЛАТНО)

**Последнее обновление:** 2026-05-08  
**Статус:** Готово к развертыванию ✅ (после выполнения критических шагов)

---

## 🚨 КРИТИЧЕСКИЕ ШАГИ (ВЫПОЛНИТЬ ПЕРЕД ДЕПЛОЕМ)

### Шаг 1: Ротирование Ключей и Генерация Новых

#### 1.1 Создать новые ключи шифрования

```bash
# Генерируем новый ENCRYPTION_KEY (32 байта, base64)
python -c "import base64, os; print('ENCRYPTION_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"

# Генерируем новую ENCRYPTION_SALT (32 байта, base64)
python -c "import base64, os; print('ENCRYPTION_SALT=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"

# Генерируем новый CSRF_SECRET_KEY (32 байта, URL-safe)
python -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Сохраните эти значения - они понадобятся при деплое.

#### 1.2 Создать новые API ключи в Supabase

1. Откройте https://app.supabase.com
2. Выберите ваш проект
3. Settings → API → Regenerate New Publishable Key
4. Settings → API → Regenerate New Service Role Key (если используется)

Новый Publishable Key нужно использовать для `SUPABASE_KEY` на Render.

#### 1.3 Изменить пароль PostgreSQL в Supabase

1. Settings → Database → Password
2. Change Password → установите новый пароль
3. Новая `DATABASE_URL` будет выглядеть так:
   ```
   postgresql://postgres.xxxxx:NEW_PASSWORD@aws-region.pooler.supabase.com:6543/postgres
   ```

---

### Шаг 2: Удалить .env из Git Истории

⚠️ **КРИТИЧНО**: Текущий .env содержит реальные учетные данные и уже в репозитории!

#### 2.1 Установить BFG Repo-Cleaner

```bash
# Windows
choco install bfg  # если используется Chocolatey
# или скачайте с https://rtyley.github.io/bfg-repo-cleaner/

# Linux/Mac
brew install bfg
```

#### 2.2 Удалить .env из истории

```bash
# 1. Убедитесь что все committed
git status

# 2. Запустите BFG
bfg --delete-files .env

# 3. Очистите рефлоги
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. Проверьте что .env удален
git log --all --full-history -- .env
# (Должно быть: fatal: your current branch appears to be empty)
```

#### 2.3 Убедитесь что .gitignore правильный

```bash
# Проверьте .gitignore содержит:
cat .gitignore | grep -E "\.env|\.env\."

# Должны быть строки:
# .env
# .env.local
# .env.*.local
```

#### 2.4 Push изменений

```bash
git push --force-with-lease origin main
# ⚠️ Это переписывает историю! Обновите рабочие копии на других машинах.
```

---

## 📋 РАЗВЕРТЫВАНИЕ НА RENDER

### Шаг 3: Создать Аккаунт на Render.com

1. Откройте https://render.com
2. Зарегистрируйтесь с GitHub (рекомендуется)
3. Подтвердите email

### Шаг 4: Подключить GitHub Репозиторий

1. Dashboard → New → Web Service
2. Connect Repository → GitHub → Select Repository (PAD+ AI)
3. Branch: `main`
4. Runtime: `Python 3.11`
5. Name: `pad-plus-ai-backend`
6. Plan: **Free** (важно!)
7. Build Command: (возьмется из render.yaml)
8. Start Command: (возьмется из render.yaml)

### Шаг 5: Установить Environment Variables

**ВАЖНО: Никогда не закоммичивайте .env в git!**

Перейдите в **Environment** → Add Environment Variable для каждого:

```
FRONTEND_URL=https://YOUR_FRONTEND_DOMAIN.onrender.com
DATABASE_URL=postgresql://postgres.xxxxx:PASSWORD@aws-region.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=sb_publishable_xxxxx
ENCRYPTION_KEY=<сгенерированный выше>
ENCRYPTION_SALT=<сгенерированный выше>
CSRF_SECRET_KEY=<сгенерированный выше>
REDIS_URL=rediss://default:PASSWORD@host.upstash.io:6379
```

### Шаг 6: Развернуть

1. Нажмите **Deploy**
2. Дождитесь окончания сборки (5-15 минут)
3. Проверьте логи: Logs → View Deployment Logs

---

## ✅ ПРОВЕРКА ПОСЛЕ ДЕПЛОЯ

### Проверка Health Status

```bash
# Замените на ваш URL
curl https://your-app.onrender.com/health

# Ответ должен быть:
# {
#   "status": "healthy",
#   "version": "4.0.0",
#   "database": "connected",
#   "cache": "connected"
# }
```

### Проверка HTTPS и Security

```bash
# 1. HTTPS должен быть автоматическим (Render обеспечивает)
curl -I https://your-app.onrender.com/health
# Должно быть: HTTP/2 200

# 2. Проверьте CORS headers
curl -H "Origin: https://your-frontend.onrender.com" https://your-app.onrender.com/health
# Должны быть: Access-Control-Allow-Origin: https://your-frontend.onrender.com
```

### Проверка Логов

```bash
# На Render Dashboard:
# Services → pad-plus-ai-backend → Logs
# Ищите:
# ✅ "ANTI_DIRECTIVE проверена"
# ✅ "Cache manager инициализирован"
# ✅ "PAD+ AI готов к работе"
```

---

## 🔒 БЕЗОПАСНОСТЬ - КОНТРОЛЬНЫЙ СПИСОК

```
ПЕРЕД PRODUCTION:
☐ .env удален из git истории (проверьте: git log --all -- .env)
☐ Все старые ключи ротированы в Supabase
☐ Новые ENCRYPTION_KEY/SALT сгенерированы
☐ Environment Variables установлены на Render (НЕ в коде)
☐ FRONTEND_URL установлен на точный домен (без wildcards)
☐ DATABASE_URL использует новый пароль
☐ REDIS_URL использует новый пароль (если отдельный сервис)
☐ Middleware включены (SecurityMiddleware, RateLimitMiddleware, CSRFMiddleware)
☐ CORS проверяет точный FRONTEND_URL (не wildcards)
☐ /health endpoint работает

ПОСЛЕ ДЕПЛОЯ:
☐ API доступен по HTTPS
☐ Health check возвращает "healthy"
☐ Логи не содержат ошибок при инициализации
☐ Rate limiting работает (проверьте много запросов подряд)
☐ CORS работает только с FRONTEND_URL
☐ File upload валидирует MIME type
☐ Все API endpoints доступны

ПОСТОЯННО:
☐ Мониторьте логи на ошибки
☐ Проверяйте использование памяти (может быть до 512MB)
☐ Ротируйте ключи каждые 90 дней
☐ Обновляйте зависимости (pip list --outdated)
```

---

## 🐛 ЧАСТЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### Проблема: Build Timeout (> 15 минут)

**Причина:** npm install слишком долгий

**Решение:**
1. Убедитесь что RAG инициализируется в фоне (уже исправлено)
2. Уменьшите количество npm зависимостей
3. Используйте npm ci вместо npm install

### Проблема: Out of Memory (OOM Kill)

**Причина:** Render free tier имеет 512MB RAM

**Решение:**
1. Отложите RAG инициализацию на фон (уже исправлено)
2. Уменьшите количество workers (используем 1)
3. Отключите ненужные компоненты

### Проблема: Database Connection Error

**Причина:** DATABASE_URL неправильный или БД недоступна

**Решение:**
1. Проверьте format: `postgresql://user:password@host:port/database`
2. Убедитесь что Supabase проект active
3. Проверьте IP whitelist в Supabase Settings

### Проблема: CORS Error

**Причина:** FRONTEND_URL не совпадает с реальным домом

**Решение:**
1. Установите правильный FRONTEND_URL на Render
2. Убедитесь что используется https:// (не http://)
3. Никаких wildcards в FRONTEND_URL

### Проблема: Health Check Failed

**Причина:** /health endpoint недоступен или возвращает ошибку

**Решение:**
1. Проверьте логи: "Ошибка при инициализации кэша"
2. Убедитесь что Redis/Cache доступна
3. Проверьте DATABASE_URL для проверки БД

---

## 🔧 ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ ПЕРЕД ДЕПЛОЕМ

```bash
# 1. Создайте локальный .env (с новыми ключами)
cp .env.example .env
# Отредактируйте с новыми значениями

# 2. Установите зависимости
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# 3. Запустите backend локально
python backend/main.py

# 4. Проверьте endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI

# 5. Проверьте фронтенд
# Откройте http://localhost:8000 в браузере
```

---

## 📞 ПОДДЕРЖКА

Если возникли проблемы:

1. **Проверьте логи:** Render Dashboard → Logs → View Deployment Logs
2. **Проверьте render.yaml:** Синтаксис, отступы, переменные окружения
3. **Проверьте Environment:** Все переменные установлены (DATABASE_URL, SUPABASE_KEY и т.д.)
4. **Проверьте git:** .env удален из истории (`git log --all -- .env`)
5. **Проверьте requirements.txt:** Все зависимости с точными версиями

---

## 📝 ИТОГОВЫЙ ЧЕКЛИСТ ДЕПЛОЯ

- [ ] Новые ключи сгенерированы
- [ ] .env удален из git истории (push --force-with-lease выполнен)
- [ ] Старые ключи ротированы в Supabase
- [ ] Render账户 создан
- [ ] GitHub репозиторий подключен
- [ ] Environment variables установлены (все, без пропусков)
- [ ] render.yaml обновлен
- [ ] Deploy запущен
- [ ] Build прошел успешно (без ошибок)
- [ ] Health check работает
- [ ] HTTPS работает
- [ ] API endpoints доступны
- [ ] Логи не содержат критических ошибок

✅ **Приложение готово к production!**
