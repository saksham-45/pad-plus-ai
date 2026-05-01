# Мониторинг PAD+ AI

## Обзор

Система мониторинга PAD+ AI построена на стеке **Prometheus + Grafana** и обеспечивает:

- Сбор и хранение метрик производительности
- Визуализация состояния системы
- Алертинг при возникновении проблем
- Мониторинг системных ресурсов

## Компоненты

### 1. Prometheus
**Порт:** `9090`

Сбор и хранение метрик из:
- PAD+ AI Backend (`/metrics`)
- Node Exporter (системные метрики)
- cAdvisor (метрики контейнеров)

### 2. Grafana
**Порт:** `3000`
**Логин/пароль:** `admin/admin`

Визуализация метрик через дашборды:
- PAD+ AI Overview - общий статус системы
- Производительность API
- Использование ресурсов

### 3. Node Exporter
**Порт:** `9100`

Системные метрики:
- CPU usage
- Memory usage
- Disk I/O
- Network I/O

### 4. cAdvisor
**Порт:** `8080`

Метрики контейнеров:
- Использование CPU/памяти на контейнер
- Сетевая активность
- Перезапуски контейнеров

### 5. Alertmanager
**Порт:** `9093`

Обработка и отправка уведомлений об алертах.

## Быстрый старт

### Запуск стека мониторинга

```bash
# Запуск всех компонентов мониторинга
docker-compose -f docker-compose.monitoring.yml up -d

# Проверка статуса
docker-compose -f docker-compose.monitoring.yml ps
```

### Остановка

```bash
docker-compose -f docker-compose.monitoring.yml down
```

### Просмотр логов

```bash
# Все логи
docker-compose -f docker-compose.monitoring.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.monitoring.yml logs -f prometheus
```

## Доступ к интерфейсам

| Сервис | URL | Примечания |
|--------|-----|------------|
| Prometheus | http://localhost:9090 | Запросы PromQL |
| Grafana | http://localhost:3000 | admin/admin |
| Node Exporter | http://localhost:9100/metrics | Сырые метрики |
| cAdvisor | http://localhost:8080 | UI + API |
| Alertmanager | http://localhost:9093 | Управление алертами |

## Метрики PAD+ AI

### Основные метрики

| Метрика | Описание |
|---------|----------|
| `padplus_uptime_seconds` | Время работы сервиса |
| `padplus_requests_total` | Общее количество запросов |
| `padplus_request_duration_seconds` | Длительность обработки запросов |
| `padplus_memory_usage_bytes` | Использование памяти |
| `padplus_cache_hits_total` | Попадания в кэш |
| `padplus_db_failures_total` | Ошибки базы данных |

### Метрики Pipeline

| Метрика | Описание |
|---------|----------|
| `padplus_pipeline_state` | Состояние pipeline (0=healthy, 1=degraded, 2=failed) |
| `padplus_pipeline_duration_seconds` | Время выполнения pipeline |
| `padplus_truth_confidence_avg` | Средняя уверенность Truth Loop |

### Метрики безопасности

| Метрика | Описание |
|---------|----------|
| `padplus_safety_blocked_total` | Заблокированные запросы |
| `padplus_validation_threats_total` | Обнаруженные угрозы |

## Алерты

### Критические алерты

| Алерт | Условие | Действие |
|-------|---------|----------|
| `PADPlusBackendDown` | Сервис недоступен 1 мин | Немедленное уведомление |
| `PADPlusPipelineFailed` | Pipeline неработоспособен | Немедленное уведомление |
| `PADPlusDBCircuitBreakerOpen` | Circuit Breaker сработал | Немедленное уведомление |
| `NodeDiskFull` | Диск заполнен >90% | Критическое уведомление |

### Предупреждения

| Алерт | Условие | Действие |
|-------|---------|----------|
| `PADPlusBackendHighErrorRate` | Ошибки >5% в течение 2 мин | Уведомление |
| `PADPlusBackendHighLatency` | p95 задержка >5 сек | Уведомление |
| `PADPlusHighMemoryUsage` | Память >90% в течение 5 мин | Уведомление |
| `NodeHighCPU` | CPU >80% в течение 5 мин | Уведомление |

## Настройка алертов

### Изменение порогов

Отредактируйте `monitoring/prometheus/alerts.yml`:

```yaml
- alert: PADPlusBackendHighErrorRate
  expr: |
    rate(padplus_requests_total{status=~"5.."}[5m]) 
    / rate(padplus_requests_total[5m]) > 0.05  # Измените порог
  for: 2m
```

### Настройка уведомлений

Отредактируйте `monitoring/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'your-email@example.com'  # Измените email
        send_resolved: true
```

### Интеграция со Slack

Раскомментируйте в `alertmanager.yml`:

```yaml
slack_configs:
  - channel: '#alerts'
    api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
```

## PromQL примеры

### Запросы для анализа

```promql
# Количество запросов в секунду
rate(padplus_requests_total[5m])

# Процент ошибок
sum(rate(padplus_requests_total{status=~"5.."}[5m])) / sum(rate(padplus_requests_total[5m])) * 100

# 95-й перцентиль задержки
histogram_quantile(0.95, rate(padplus_request_duration_seconds_bucket[5m]))

# Использование памяти в процентах
(padplus_memory_usage_bytes / padplus_memory_total_bytes) * 100

# Hit rate кэша
rate(padplus_cache_hits_total[5m]) / rate(padplus_cache_requests_total[5m]) * 100

# Загрузка CPU
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## Интеграция с основным приложением

### Включение метрик

Метрики автоматически собираются при запуске приложения. Эндпоинт `/metrics` доступен по умолчанию.

### Пользовательские метрики

Добавление пользовательских метрик в код:

```python
from core.metrics_collector import get_metrics

metrics = get_metrics()

# Счетчик
metrics.increment("custom_counter", labels={"type": "special"})

# Gauge
metrics.set_gauge("custom_gauge", 42.0)

# Гистограмма
metrics.record_value("custom_duration", 123.45)
```

## Troubleshooting

### Prometheus не видит цели

1. Проверьте, что backend запущен:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Проверьте конфигурацию Prometheus:
   ```bash
   docker exec padplus-prometheus cat /etc/prometheus/prometheus.yml
   ```

### Grafana не показывает данные

1. Проверьте datasource в Grafana (Configuration → Data Sources → Prometheus)
2. URL должен быть: `http://prometheus:9090`

### Алерты не отправляются

1. Проверьте конфигурацию Alertmanager:
   ```bash
   docker exec padplus-alertmanager cat /etc/alertmanager/alertmanager.yml
   ```

2. Проверьте логи Alertmanager:
   ```bash
   docker logs padplus-alertmanager
   ```

## Безопасность

### Ограничение доступа

Для production рекомендуется:

1. Настроить аутентификацию в Grafana:
   ```ini
   [auth.anonymous]
   enabled = false
   ```

2. Использовать reverse proxy (nginx) с HTTPS

3. Ограничить доступ к Prometheus:
   ```yaml
   # prometheus.yml
   global:
     external_labels:
       environment: 'production'
   ```

### Чувствительные данные

Не храните пароли и API ключи в конфигурационных файлах. Используйте:
- Environment variables
- Docker secrets
- Vault или аналоги

## Дополнительные ресурсы

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)