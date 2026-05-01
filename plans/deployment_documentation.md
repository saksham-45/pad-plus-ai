# Документация по развертыванию PAD+ AI

## Обзор

Данный документ описывает различные способы развертывания системы PAD+ AI, включая локальный запуск, контейнеризацию и облачное развертывание.

## Системные требования

### Минимальные требования
- **CPU**: 2 ядра
- **RAM**: 4 ГБ
- **Storage**: 2 ГБ свободного места
- **OS**: Linux, macOS, Windows 10+

### Рекомендуемые требования
- **CPU**: 4+ ядра
- **RAM**: 8+ ГБ
- **Storage**: SSD с 10+ ГБ свободного места

## Локальное развертывание

### Подготовка окружения

1. Установите Python 3.10 или выше:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3.11-dev
   
   # macOS
   brew install python@3.11
   
   # Windows
   # Скачайте с python.org
   ```

2. Установите Node.js 16+:
   ```bash
   # Используйте nvm для управления версиями
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install node
   nvm use node
   ```

### Установка и запуск

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/padplus-ai.git
   cd padplus-ai
   ```

2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # или
   venv\Scripts\activate  # Windows
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```

4. Настройте переменные окружения:
   ```bash
   cp .env.example .env
   # Отредактируйте .env с вашими API ключами
   ```

5. Запустите систему:
   ```bash
   # В одном терминале
   cd backend && uvicorn main:app --reload --port 8000
   
   # В другом терминале
   cd frontend && npm run dev
   ```

6. Откройте http://localhost:5173

## Контейнеризированное развертывание

### Подготовка Dockerfile

Используйте предоставленные Dockerfile для backend и frontend:

**Для backend**:
```bash
# Сборка образа
docker build -f plans/Dockerfile.backend -t padplus-ai-backend .

# Запуск контейнера
docker run -d -p 8000:8000 -e OPENROUTER_API_KEY=your_key_here padplus-ai-backend
```

**Для frontend**:
```bash
# Сборка образа
docker build -f plans/Dockerfile.frontend -t padplus-ai-frontend .

# Запуск контейнера
docker run -d -p 3000:80 --env VITE_API_URL=http://localhost:8000 padplus-ai-frontend
```

### Использование docker-compose

Для удобства локальной разработки создайте файл `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: plans/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DATABASE_URL=sqlite:///./data/memory.db
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  frontend:
    build:
      context: .
      dockerfile: plans/Dockerfile.frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

Запуск:
```bash
docker-compose up -d
```

## Облачное развертывание

### На платформе Render

1. Подготовьте репозиторий с обновленным `render.yaml`:
   ```yaml
   services:
     - type: web
       name: padplus-ai-backend
       runtime: python
       region: frankfurt
       plan: free
       buildCommand: pip install -r requirements.txt
       startCommand: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
       healthCheckPath: /health
       envVars:
         - key: PYTHON_VERSION
           value: "3.11.0"
         - key: OPENROUTER_ENABLED
           value: "true"
         - key: OPENROUTER_API_KEY
           sync: false
         - key: DEBUG
           value: "false"
       disk:
         name: padplus-data
         mountPath: /opt/render/project/data
         sizeGB: 1

     - type: static
       name: padplus-ai-frontend
       region: frankfurt
       plan: free
       buildCommand: cd frontend && npm install && npm run build
       path: ./frontend
       envVars:
         - key: VITE_API_URL
           value: "https://padplus-ai-backend.onrender.com"
   ```

2. Создайте аккаунт на [Render.com](https://render.com)

3. Создайте новое Web Service, подключившись к вашему GitHub репозиторию

4. Укажите:
   - Ветку: `main`
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`

5. Установите переменные окружения:
   - `OPENROUTER_API_KEY`: ваш API ключ
   - `PYTHON_VERSION`: "3.11.0"

6. Разверните приложение

### На других платформах

#### Heroku
1. Создайте `Procfile`:
   ```
   web: cd backend && gunicorn main:app -w 4 -b 0.0.0.0:$PORT
   ```

2. Используйте Heroku CLI:
   ```bash
   heroku create your-app-name
   heroku config:set OPENROUTER_API_KEY=your_key_here
   git push heroku main
   ```

#### DigitalOcean App Platform
1. Создайте `Dockerfile` для всего приложения
2. Используйте DigitalOcean App Platform для автоматического деплоя

## Настройка домена

После развертывания вы можете настроить собственный домен:

1. Добавьте DNS запись, указывающую на IP вашего сервера или URL платформы
2. Настройте SSL сертификат (если поддерживается платформой)
3. Обновите `VITE_API_URL` переменную окружения в соответствии с новым доменом

## Мониторинг и обслуживание

### Логирование

Система PAD+ AI использует встроенное логирование Python. Логи доступны:

- В консоли при локальном запуске
- В панели управления облачной платформы
- В файле `logs/app.log` (если настроено)

### Метрики

Для мониторинга производительности используйте:

- Встроенный эндпоинт `/health` для проверки состояния
- Эндпоинт `/api/v1/analytics/report` для получения статистики
- WebSocket соединение для получения реального времени событий

### Резервное копирование

Регулярно создавайте резервные копии:

- Базы данных (SQLite файлы в `data/`)
- Файлов конфигурации
- Переменных окружения

### Обновления

Для обновления системы:

1. Сделайте бекап текущей версии
2. Обновите репозиторий: `git pull origin main`
3. Обновите зависимости: `pip install -r requirements.txt`
4. Перезапустите приложение

## Устранение неполадок

### Распространенные проблемы

#### 1. Ошибка запуска backend
- Проверьте версию Python
- Убедитесь, что все зависимости установлены
- Проверьте переменные окружения

#### 2. Ошибка подключения к LLM
- Проверьте API ключи
- Убедитесь, что провайдер LLM включен
- Проверьте подключение к интернету

#### 3. Проблемы с памятью
- Увеличьте размер диска (если используется Render)
- Проверьте права на запись в директорию `data/`
- Запустите процедуру гигиены памяти

#### 4. Ошибки CORS
- Проверьте настройки `FRONTEND_URL` в переменных окружения
- Убедитесь, что домен правильно указан

### Диагностика

Для диагностики проблем:

1. Проверьте логи приложения
2. Используйте эндпоинт `/api/v1/mind-state` для проверки состояния системы
3. Проверьте `/health` эндпоинт
4. Используйте веб-интерфейс для визуализации состояния

## Безопасность

### Рекомендации

- Не храните API ключи в коде
- Используйте HTTPS для всех соединений
- Регулярно обновляйте зависимости
- Ограничьте доступ к административным эндпоинтам
- Мониторьте логи на подозрительную активность

### Защита

Система включает встроенные механизмы защиты:
- Rate limiting
- Input validation
- Anti-injection measures
- Session management

## Поддержка

Для получения помощи:
- Проверьте документацию в директории `docs/`
- Создайте Issue в репозитории
- Обратитесь к файлу `SUPPORT.md` (если доступен)