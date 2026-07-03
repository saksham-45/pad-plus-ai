# X-Ray: Руководство по системе наблюдаемости

X-Ray = полная трассировка того, как система думает и что реально делает.

Не логирование. Не debug. Система видит себя, находит свои проблемы и предлагает решения.

---

## Философия

Без X-Ray: ты веришь системе. Половина кода мёртвая.

С X-Ray: ты видишь правду. Кто вызвался, порядок, время, результат.

## Архитектура (актуальная)

```
Компоненты:

СБОР ДАННЫХ:
  TraceCollector          — сбор событий пайплайна (core)
  XRayTraceCollector      — сбор трейсов X-Ray (TraceSession, TraceEvent)
  XRayTracer              — создание/завершение трейсов (Span, Trace)
  TraceContext            — распределённая трассировка (OpenTelemetry-стиль)

ВИЗУАЛИЗАЦИЯ:
  ThoughtStream           — мысли AI в реальном времени
  CognitiveState          — когнитивные метрики (uncertainty, confidence)
  XRayBroadcaster         — WebSocket трансляция по каналам

САМОДИАГНОСТИКА:
  HealerListener          — подписка на события пайплайна
  run_diagnostics         — запуск 5 детекторов
  ReflectionLoop          — мета-анализ: learnings + changes + stats
  HealingChangesStore     — хранилище изменений с rollback

МЕТА-ОБУЧЕНИЕ:
  MetaLearner             — обучение на стратегиях
  InsightsEngine          — аналитика
  ReflectionEngine        — самоанализ

HEALER (интеграция):
  HealerBridge            — мост PAD+ → HEALER TraceStore
  HEALER Orchestrator     — полный цикл: diagnose → patch → verify → apply/rollback

9 фаз пайплайна:
  safety → intent → retrieve → persona → generate → verify → remember → emit → complete
```

## X-Ray тестирование

Тесты проверяют ПРОЦЕСС, а не результат. Через подписку на TraceCollector.

### Сценарии:
1. **Monolith**: 20 фаз, порядок, длительности
2. **Anti-loop**: блокировка цикла
3. **Safety block**: блокировка безопасности
4. **Strategy**: выбор стратегии от запроса
5. **Degradation**: деградация non-critical
6. **Thought stream**: мысли AI для фаз

### HEALER тесты:
1. **ReflectionLoop**: пустые циклы, ошибки, фиксы, смешанные статусы (7 тестов)
2. **ChangesStore**: apply, rollback, статусы, изоляция (7 тестов)

### Запуск:
```bash
pytest tests/test_xray/ -v
pytest tests/test_healing/ -v
```

---

## Статус (2026-07-03)

### X-Ray:
- Полный цикл трассировки: Trace → Span → TraceSession → Broadcast
- 9 фаз пайплайна с мыслями AI
- WebSocket: 8 каналов (trace, thought, emotion, decision, pipeline, system, healer, all)
- UI: дашборд, таймлайн, трейсы, поток мыслей
- REST API: полный набор endpoints

### HEALER (самодиагностика):
- 5 детекторов: SlowPhases, ErrorPath, BrokenPhases, ProviderHealth, StrategyDrift
- 3 режима: monitor (только наблюдение), suggest (диагностика + рекомендации), auto (полный цикл)
- ReflectionLoop: stats + learnings + changes
- HealingChangesStore: backup файлов, rollback по patch_id
- WS broadcast: cycle_complete, reflection, diag_event
- Frontend: HealerPage, HealerReflectionPanel (WS + polling 30s + rollback)
- Bridge к HEALER Orchestrator: diagnose → patch → verify → apply/rollback

### Интеграция:
- HealerBridge ↔ XRayTraceCollector (через main.py lifecycle)
- HealerListener ↔ core TraceCollector (через main.py lifecycle)
- WS manager внедрён в healer_routes для broadcast
- Reflection broadcast после каждого healing cycle

---

## Правила для разработчика

1. Каждый компонент → подписка на TraceCollector, а не лог
2. Каждый новый endpoint → X-Ray трейс
3. UI не делает запросов без обратной связи
4. WebSocket events все проходят через broadcaster, а не напрямую
5. DiagnosticReport теперь содержит: status, old_value, new_value, timestamp
6. HealingChangesStore применяется для всех auto-fix патчей
7. Все rollback операции проходят через POST /api/v1/healer/bridge/rollback/{patch_id}
