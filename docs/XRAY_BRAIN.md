# X-Ray: Brain File для новой сессии

## Что такое X-Ray
Система наблюдаемости AI. Не UI-страница, а уровень observability, вшитый в каждый запрос.

## Девиз
Тест падает -> чини СИСТЕМУ, не тест.

## Суть X-Ray тестирования
Тесты проверяют ПРОЦЕСС, а не результат.
Обычный тест: assert result.success
X-Ray тест: assert "generate" in trace_stages

## Data Flow
Request -> Pipeline Executor
  +-> trace_collector.start_session()
  +-> trace_collector.record_event() x 20
  +-> broadcaster.send_thought/send_pipeline_status
  +-> trace_collector.complete_session()
  +-> подписчики TraceCollector: WebSocket + тесты

## Статус (2026-06-08)
6 X-Ray тестов, 55 pipeline тестов, все зелёные.
Pipeline: 20 фаз, ~4.8s (RAG 0.9s, generate 3.8s)

## Что починено в этой сессии
- RAG DB timeout: 20s -> 0.9s (connect_timeout=3)
- sentence_transformers: 15s -> 0s (ленивый импорт)
- full_model=None при неизвестном провайдере
- success=True при пустом ответе -> False
- History count=exact без limit(0) -> висел 30min
- Stats IN запрос -> message_count из dialogs
- Dialogs trigger NEW.dialog_id (несовместимость)
- Chat messages sessionStorage между вкладками
- Корень: 53 -> 27 записей

## Как писать X-Ray тест
trace_events фикстура -> collector.subscribe() -> выполнить pipeline -> проверить phases

## Ключевые файлы
backend/core/xray/trace_collector.py
backend/core/xray/broadcaster.py
backend/core/xray/thought_visualizer.py
backend/core/pipeline/executor.py
tests/test_xray/
docs/XRAY_GUIDE.md

## Текущие задачи
См. docs/XRAY_BRAIN_TASKS.md
