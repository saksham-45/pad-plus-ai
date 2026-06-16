# 📚 Документация PAD+ AI

## Актуальные документы (10 файлов)

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура системы, Pipeline, Память, Эмоции |
| [STABILIZATION_PLAN.md](STABILIZATION_PLAN.md) | Текущий план стабилизации (v2.1) |
| [API.md](API.md) | API эндпоинты и их использование |
| [XRAY.md](XRAY.md) | X-RayBrain — система полной наблюдаемости |
| [XRAY_GUIDE.md](XRAY_GUIDE.md) | Руководство по X-Ray |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Руководство по деплою на production |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | Аудит безопасности и качества кода |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Структура проекта и файлов |
| [RLS_POLICIES.md](RLS_POLICIES.md) | RLS политики базы данных |
| `README.md` | Этот файл |

## Устаревшая документация

**77 файлов** сохранено в [archive/legacy/](archive/legacy/):
- Устаревшие планы (план.md, PHASE*_PLAN.md)
- Временные багфиксы (BUGFIX_*.md)
- Дублирующие руководства (SETUP.md, STARTUP_GUIDE.md)
- Устаревшие инструкции (RLS_FIX_*.md)
- Модульные описания (BACKEND.md, FRONTEND.md и др.)

---

## Быстрый старт

### Запуск backend
```bash
cd backend
uvicorn main:app --reload --port 8080
```

### Запуск frontend
```bash
cd frontend
npm run dev
```

Откройте http://localhost:5174

---

## Структура проекта

```
PAD+ AI/
├── backend/           # FastAPI backend
│   ├── api/          # API routes
│   ├── core/         # Ядро системы
│   ├── memory/       # Системы памяти
│   ├── emotion/      # Эмоциональная модель
│   └── runtime/      # Provider management
├── frontend/         # React frontend
│   ├── src/
│   │   ├── pages/
│   │   └── components/
│   └── public/
├── docs/             # Документация (этот каталог)
└── tests/            # Тесты
```

---

## Поддерживаемые провайдеры

- **GigaChat** — OAuth, бесплатно с лимитами
- **OpenRouter** — API Key, есть бесплатные модели
- **Groq** — API Key, бесплатно с лимитами
- **Google Gemini** — API Key, бесплатно с лимитами
- **OpenAI** — API Key, платно
- **Anthropic Claude** — API Key, платно

---

## Лицензия

Proprietary. Все права защищены.
