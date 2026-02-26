# Dockerfile для backend PAD+ AI

```dockerfile
# Используем официальный образ Python
FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для данных
RUN mkdir -p data

# Экспортируем порт
EXPOSE $PORT 8000

# Команда запуска
CMD ["sh", "-c", "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## Описание

Этот Dockerfile предназначен для контейнеризации backend части системы PAD+ AI. Он:

1. Использует официальный образ Python 3.11
2. Устанавливает необходимые системные зависимости
3. Устанавливает зависимости Python из requirements.txt
4. Копирует все файлы проекта
5. Создает директорию для данных
6. Настроен на работу с переменной PORT для облачных платформ
7. Запускает backend приложение через uvicorn