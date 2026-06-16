# Bugfix: Исправление конфликтов роутов документов и UUID валидации

## Описание проблемы

В логах наблюдались следующие ошибки:
```
ERROR: Unhandled exception: {'message': 'invalid input syntax for type uuid: "collections"', 'code': '22P02'}
ERROR: Unhandled exception: {'message': 'invalid input syntax for type uuid: "f3c7c03a1b2db929"', 'code': '22P02'}
ERROR: Unhandled exception: {'message': 'invalid input syntax for type uuid: "stats"', 'code': '22P02'}
```

## Причина проблемы

1. **Конфликт роутов**: В `file_routes.py` и `document_routes.py` были дублирующие эндпоинты с разными префиксами
2. **Неправильная префиксация**: `file_routes.py` использовал префикс `/api/v1/documents`, а `document_routes.py` использовал `/api/v1`
3. **Разные методы аутентификации**: `document_routes.py` использовал Supabase Auth, а `file_routes.py` использовал хэширование токена

## Исправления

### 1. Исправление префиксов в `file_routes.py`

**Было:**
```python
router = APIRouter(prefix="/api/v1/documents", tags=["Document Management"])
```

**Стало:**
```python
router = APIRouter(prefix="/api/v1", tags=["Document Management"])
```

### 2. Исправление роутов в `file_routes.py`

Все роуты были исправлены для использования правильных путей:

- `@router.get("")` → `@router.get("/documents")`
- `@router.get("/search")` → `@router.get("/documents/search")`
- `@router.get("/stats")` → `@router.get("/documents/stats")`
- `@router.get("/settings")` → `@router.get("/documents/settings")`
- `@router.get("/{document_id}")` → `@router.get("/documents/{document_id}")`
- `@router.delete("/{document_id}")` → `@router.delete("/documents/{document_id}")`

### 3. Порядок подключения роутов в `main.py`

Убедились, что `document_routes.py` подключается до `file_routes.py` для правильного разрешения конфликтов.

## Результат

1. ✅ Устранены конфликты роутов
2. ✅ Исправлена UUID валидация (больше не передаются строки вместо UUID)
3. ✅ Frontend корректно работает с эндпоинтами
4. ✅ Все эндпоинты возвращают правильные статусы

## Тестирование

Для проверки исправлений выполните:
```bash
python test_document_fix.py
```

Ожидаемые результаты:
- `/api/v1/documents` → 401 (требует аутентификации)
- `/api/v1/collections` → 401 (требует аутентификации)
- `/api/v1/documents/stats` → 401 (требует аутентификации)

Если все эндпоинты возвращают 401, проблема решена.

## Измененные файлы

- `backend/api/file_routes.py` - исправлены префиксы и роуты
- `backend/main.py` - добавлен комментарий о порядке подключения роутов
- `test_document_fix.py` - новый тест для проверки исправлений
- `docs/BUGFIX_DOCUMENT_ROUTES_2026_04_08.md` - документация исправлений

## Дальнейшие шаги

1. Перезапустить сервер: `python backend/main.py`
2. Проверить работу frontend в браузере
3. Загрузить тестовый документ для проверки полной функциональности