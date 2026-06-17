# PAD+ AI v4.0 — План развития и оптимизации

## ✅ Завершено (текущий релиз)

- [x] Развёртывание на Render (Python backend + Uvicorn)
- [x] Supabase Auth — регистрация/логин (rate limit bypass через Admin API)
- [x] Supabase Storage — bucket `documents` с RLS
- [x] База данных — таблицы users, user_api_keys, dialogs, messages, documents, document_collections, user_settings
- [x] RAG Memory v3.0 (PostgreSQL) — хранение диалогов
- [x] Redis (Upstash) — кэширование
- [x] X-Ray — мониторинг и трассировка
- [x] Healer — самодиагностика
- [x] WebSocket — real-time чат
- [x] Шифрование ключей — стабильная fallback-соль

## 🔴 Критические (блокирует функционал)

- [ ] Пайплайн обработки документов (извлечение текста → RAG)
  - Установка: PyMuPDF (PDF), python-docx (DOCX), python-pptx (PPTX)
  - Модуль `backend/core/document_processor.py`
  - Извлечение текста + чанкинг
  - Векторизация и сохранение в pgvector
  - Поиск релевантных чанков при ответе AI
- [ ] Обработка ошибок при недоступности провайдера AI
  - Graceful fallback на другой ключ/провайдер
  - Понятное сообщение пользователю
- [ ] Rate limiter для чата (защита от DDOS и перерасхода ключей)

## 🟡 Высокий приоритет

- [ ] Soft-delete и корзина для документов
- [ ] Пагинация диалогов (сейчас базовая)
- [ ] Поиск по истории диалогов
- [ ] Экспорт диалогов (JSON/TXT/PDF)
- [ ] Очистка устаревших RAG-диалогов (авто-ротация)
- [ ] Graceful shutdown — сохранение состояния перед выключением

## 🟢 Средний приоритет

- [ ] Свой домен (CNAME → Render)
- [ ] CI/CD — GitHub Actions: линтер, тесты перед деплоем
- [ ] Pytest для критических модулей (auth, encryption, rag)
- [ ] Sentry / логирование ошибок
- [ ] Health check endpoint — deep check всех компонентов
- [ ] Prometheus метрики для Render
- [ ] Telegram-уведомления о падении сервиса
- [ ] Кэширование списка ключей (сейчас прямой запрос к БД каждый раз)
- [ ] Connection pool для PostgreSQL (сейчас одно соединение)

## 🔵 Низкий приоритет / Идеи

- [ ] Поддержка изображений в чате (vision models)
- [ ] TTS / голосовой ввод
- [ ] Мобильное PWA (установка на телефон)
- [ ] Multi-tenant: разделение пользователей по organisations
- [ ] API ключи сторонних разработчиков
- [ ] Webhook-интеграции (Telegram, Slack)
- [ ] Локализация (EN интерфейс)
- [ ] Тёмная/светлая тема (уже частично)
- [ ] История изменений файлов (versioning)

## 🐛 Найденные баги (todo)

_Добавляйте сюда при тестировании_

- [ ] <!-- формат: дата — описание — статус -->
