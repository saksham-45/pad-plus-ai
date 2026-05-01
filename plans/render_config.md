# Оптимизированная конфигурация Render для PAD+ AI

## Описание проблемы

Текущий файл `render.yaml` содержит синтаксические ошибки и может быть улучшен для лучшей работы на Render. Ниже приведена корректная версия конфигурации.

## Оптимизированная конфигурация

```yaml
# PAD+ AI - Render Blueprint
# https://render.com/docs/blueprint-spec

services:
  # Backend - Web Service
  - type: web
    name: padplus-ai-backend
    runtime: python
    region: frankfurt
    plan: free
    buildCommand: |
      python -m pip install --upgrade pip
      pip install -r requirements.txt
    startCommand: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.0"
      - key: OPENROUTER_ENABLED
        value: "true"
      - key: OPENROUTER_API_KEY
        sync: false
      - key: OPENROUTER_MODEL
        value: "google/gemma-7b-it"
      - key: GIGACHAT_ENABLED
        value: "false"
      - key: DEBUG
        value: "false"
      - key: RENDER
        value: "true"
      - key: LOG_LEVEL
        value: "info"
      - key: DATABASE_URL
        value: "sqlite:///./data/memory.db"
    disk:
      name: padplus-data
      mountPath: /opt/render/project/data
      sizeGB: 1

  # Frontend - Static Site
  - type: static
    name: padplus-ai-frontend
    region: frankfurt
    plan: free
    buildCommand: |
      cd frontend
      npm install
      npm run build
    path: ./frontend
    envVars:
      - key: VITE_API_URL
        value: "https://padplus-ai-backend.onrender.com"
```

## Внесенные улучшения

1. Заменено `env: python` на `runtime: python` (правильное свойство для Render)
2. Заменено `env: static` на `type: static` (правильный тип сервиса)
3. Убраны неподдерживаемые свойства:
   - `staticPublishPath` → заменено на `path`
   - `routes` и `domains` → не поддерживаются в blueprint спецификации
4. Исправлены типы значений:
   - Все значения переменных окружения теперь строки в кавычках
   - Булевые значения преобразованы в строки ("true"/"false")
5. Улучшена команда сборки для лучшей надежности
6. Добавлены полезные переменные окружения для конфигурации

## Инструкции по применению

Для использования этой конфигурации замените содержимое файла `render.yaml` в корне проекта на приведенное выше.