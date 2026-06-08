# X-Ray: Система наблюдаемости AI

X-Ray = полная трассировка того, как система думает и что реально делает.

Не логирование. Не debug. Система видит себя, находит свои проблемы и предлагает решения.

---

## Философия

Без X-Ray: ты веришь системе. Половина кода мёртвая.

С X-Ray: ты видишь правду. Кто вызвался, порядок, время, результат.

---

## Архитектура

Компоненты:
- TraceCollector: сбор событий pipeline
- XRayBroadcaster: WebSocket трансляция
- ThoughtVisualizer: мысли AI
- SystemState: состояние системы
- MetaLearner: статистика стратегий
- ReflectionLoop: саморефлексия
- InsightsEngine: аналитика
- CognitiveState: PAD метрики

TraceStage:
safety -> intent -> retrieve -> persona -> generate -> verify -> remember -> emit -> complete

---

## X-Ray Тестирование

Тесты проверяют ПРОЦЕСС, а не результат.
Через подписку на TraceCollector.

Сценарии:
1. Monolith: 20 фаз, порядок, длительности
2. Anti-loop: блокировка цикла
3. Safety block: блокировка безопасности
4. Strategy: выбор стратегии от запроса
5. Degradation: деградация non-critical
6. Thought stream: мысли AI для фаз

Запуск: pytest tests/test_xray/ -v

---

## Статус (2026-06-08)

6 тестов, все зелёные, 3.6s.

Починено:
- memory/ дубликат удалён
- sentence_transformers (15s) -> ленивый импорт
- safety block success=False
- error path complete_session

Открыто:
- fact_memory импорт (2 теста)
- два WebSocket (X-Ray + generic)
- REST /xray/latest без persistence

План: P0-P2 готово. P3: инфраструктура WS/REST. P4: мета-наблюдаемость.

---

## Правила для разработчика

1. Каждый компонент -> подписка на TraceCollector, а не лог
2. Каждый error path -> complete_session()
3. Нет top-level heavy импортов (урок 15s)
4. X-Ray тест пишется до или вместе с кодом, не после
5. Тест падает -> чини СИСТЕМУ, не тест
