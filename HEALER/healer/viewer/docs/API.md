# API HEALER Viewer

Базовый URL: `http://127.0.0.1:8085`

## GET endpoints

### Статус

```
GET /api/status
```

Ответ:
```json
{
  "app": "healer-viewer",
  "version": "0.1.0",
  "timestamp": "2026-06-09T12:00:00+00:00",
  "xray": true,
  "healer_available": true,
  "trace_store": "C:\\...\\data\\trace_store"
}
```

### Трейсы HEALER

```
GET /api/traces
```

Читает трейсы HEALER из `../HEALER/data/trace_store/`.

Ответ:
```json
{
  "count": 15,
  "traces": [
    {
      "trace_id": "abc123",
      "name": "test.scenario",
      "status": "ok",
      "started_at": 1717000000.0,
      "ended_at": 1717000001.0,
      "duration_ms": 1000.0,
      "span_count": 5
    }
  ]
}
```

### Детали трейса

```
GET /api/trace/<trace_id>
```

Ответ: полная информация о трейсе + список спанов + дерево.

### Свои трейсы (viewer)

```
GET /api/server-traces
```

Трейсы самого viewer из `data/trace_store/`.

### Запустить HEALER диагностику

```
GET /api/invoke-healer
```

Viewer вызывает HEALER через прямой Python-импорт и возвращает результат.

Ответ:
```json
{
  "success": true,
  "report_count": 42,
  "error_count": 8,
  "target": "C:\\...\\data\\trace_store",
  "timestamp": "2026-06-09T12:00:00+00:00"
}
```

### Последний результат диагностики

```
GET /api/healer-result
```

Ответ:
```json
{
  "timestamp": "2026-06-09T12:00:00+00:00",
  "report_count": 42,
  "reports": [
    {
      "detector": "SpanAnalyzer",
      "severity": "warning",
      "category": "integrity",
      "trace_id": "abc",
      "span_id": "def",
      "location": "span healer.diagnostics (abc)",
      "message": "Span healer.diagnostics не завершён",
      "recommendation": "Добавить вызов span.end() во все ветки выполнения"
    }
  ]
}
```

## POST endpoints

### Запустить патч

```
POST /api/patch
Content-Type: application/json

{
  "source_path": "viewer.py",
  "detector": "SpanAnalyzer",
  "message": "span not ended"
}
```

Ответ (успех):
```json
{
  "success": true,
  "pattern": "try_finally",
  "source_path": "viewer.py",
  "diff": "--- viewer.py\n+++ viewer.py (patched)\n...",
  "original_code": "def foo():\n    ...",
  "patched_code": "def foo():\n    try:\n        ...\n    finally:\n        cleanup()",
  "metadata": {"patched_functions": ["foo"]}
}
```

Ответ (нет изменений):
```json
{
  "success": false,
  "error": "No changes made",
  "pattern": "close_resource"
}
```

### Применить патч

```
POST /api/patch/apply
Content-Type: application/json

{
  "source_path": "viewer.py",
  "original_code": "...",
  "patched_code": "..."
}
```

Ответ:
```json
{
  "success": true,
  "source_path": "viewer.py",
  "backup": "viewer.py.healer.bak"
}
```

### Откатить патч

```
POST /api/patch/rollback
Content-Type: application/json

{
  "source_path": "viewer.py"
}
```

Ответ:
```json
{
  "success": true,
  "message": "Восстановлен: viewer.py"
}
```

## Ошибки

Все endpoints возвращают:
```json
{"success": false, "error": "описание ошибки"}
```
