# Система Аналитики

Этот документ описывает систему аналитики в PAD+ AI.

## Обзор

Система аналитики обеспечивает:

- Сбор и анализ метрик производительности
- Мониторинг использования системы
- Анализ поведения пользователей
- Отслеживание эффективности ИИ
- Генерацию отчетов и визуализаций

## Архитектура аналитики

### Компоненты

1. **MetricsCollector** - Сбор метрик
2. **AnalyticsProcessor** - Обработка аналитики
3. **PerformanceMonitor** - Монитор производительности
4. **UserBehaviorAnalyzer** - Анализ поведения пользователей
5. **ReportGenerator** - Генератор отчетов

### Типы метрик

```python
METRIC_TYPES = {
    # Системные метрики
    "system": {
        "cpu_usage": "Использование CPU",
        "memory_usage": "Использование памяти",
        "disk_usage": "Использование диска",
        "response_time": "Время ответа",
        "error_rate": "Частота ошибок"
    },
    
    # Метрики ИИ
    "ai": {
        "token_usage": "Использование токенов",
        "model_performance": "Производительность моделей",
        "emotion_stability": "Эмоциональная стабильность",
        "goal_completion": "Выполнение целей",
        "learning_progress": "Прогресс обучения"
    },
    
    # Пользовательские метрики
    "user": {
        "session_duration": "Длительность сессии",
        "interaction_frequency": "Частота взаимодействий",
        "satisfaction_score": "Уровень удовлетворенности",
        "feature_usage": "Использование функций",
        "retention_rate": "Уровень удержания"
    },
    
    # Бизнес метрики
    "business": {
        "conversion_rate": "Коэффициент конверсии",
        "user_engagement": "Вовлеченность пользователей",
        "feature_adoption": "Принятие функций",
        "revenue_impact": "Влияние на доход",
        "cost_efficiency": "Эффективность затрат"
    }
}
```

## MetricsCollector

### Сбор метрик

```python
class MetricsCollector:
    def __init__(self):
        self.metrics_storage = {}
        self.collection_interval = 60  # секунд
        self.active_collectors = {}
        
    def start_collection(self):
        """Запуск сбора метрик"""
        # Запуск фоновых задач сбора
        asyncio.create_task(self.collect_system_metrics())
        asyncio.create_task(self.collect_ai_metrics())
        asyncio.create_task(self.collect_user_metrics())
        
    async def collect_system_metrics(self):
        """Сбор системных метрик"""
        while True:
            try:
                # Сбор метрик системы
                system_metrics = await self.gather_system_metrics()
                
                # Сохранение метрик
                await self.store_metrics("system", system_metrics)
                
                # Отправка событий
                await self.publish_metrics_event("system", system_metrics)
                
            except Exception as e:
                logger.error(f"System metrics collection failed: {e}")
                
            await asyncio.sleep(self.collection_interval)
            
    async def gather_system_metrics(self) -> dict:
        """Сбор системных метрик"""
        import psutil
        import time
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Network stats
        network = psutil.net_io_counters()
        
        # Process stats
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory_percent,
            "disk_usage": disk_percent,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "process_memory_mb": process_memory,
            "timestamp": datetime.now().isoformat()
        }
```

### Сбор метрик ИИ

```python
async def collect_ai_metrics(self):
    """Сбор метрик ИИ"""
    while True:
        try:
            # Сбор метрик ИИ компонентов
            ai_metrics = await self.gather_ai_metrics()
            
            # Сохранение метрик
            await self.store_metrics("ai", ai_metrics)
            
            # Отправка событий
            await self.publish_metrics_event("ai", ai_metrics)
            
        except Exception as e:
            logger.error(f"AI metrics collection failed: {e}")
            
        await asyncio.sleep(self.collection_interval)
        
    async def gather_ai_metrics(self) -> dict:
        """Сбор метрик ИИ"""
        # Токены
        token_usage = await self.get_token_usage()
        
        # Производительность моделей
        model_performance = await self.get_model_performance()
        
        # Эмоциональная стабильность
        emotion_stability = await self.get_emotion_stability()
        
        # Цели
        goal_progress = await self.get_goal_progress()
        
        return {
            "token_usage": token_usage,
            "model_performance": model_performance,
            "emotion_stability": emotion_stability,
            "goal_progress": goal_progress,
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_token_usage(self) -> dict:
        """Получение статистики использования токенов"""
        # Сбор статистики по всем провайдерам
        total_tokens = 0
        provider_tokens = {}
        
        for provider_name, provider in self.active_collectors.items():
            if hasattr(provider, 'get_token_usage'):
                usage = await provider.get_token_usage()
                provider_tokens[provider_name] = usage
                total_tokens += usage.get("total", 0)
                
        return {
            "total_tokens": total_tokens,
            "provider_breakdown": provider_tokens,
            "cost_estimate": self.calculate_cost_estimate(provider_tokens)
        }
        
    def calculate_cost_estimate(self, provider_tokens: dict) -> float:
        """Расчет оценочной стоимости"""
        total_cost = 0.0
        
        # Стоимость по провайдерам (в USD за 1000 токенов)
        cost_rates = {
            "openai": 0.002,
            "anthropic": 0.003,
            "google": 0.0015,
            "openrouter": 0.001
        }
        
        for provider, usage in provider_tokens.items():
            rate = cost_rates.get(provider, 0.002)  # Стандартная ставка
            tokens = usage.get("total", 0)
            cost = (tokens / 1000) * rate
            total_cost += cost
            
        return total_cost
```

### Сбор пользовательских метрик

```python
async def collect_user_metrics(self):
    """Сбор пользовательских метрик"""
    while True:
        try:
            # Сбор метрик пользователей
            user_metrics = await self.gather_user_metrics()
            
            # Сохранение метрик
            await self.store_metrics("user", user_metrics)
            
            # Отправка событий
            await self.publish_metrics_event("user", user_metrics)
            
        except Exception as e:
            logger.error(f"User metrics collection failed: {e}")
            
        await asyncio.sleep(self.collection_interval)
        
    async def gather_user_metrics(self) -> dict:
        """Сбор пользовательских метрик"""
        # Активные сессии
        active_sessions = await self.get_active_sessions()
        
        # Частота взаимодействий
        interaction_stats = await self.get_interaction_stats()
        
        # Уровень удовлетворенности
        satisfaction_score = await self.get_satisfaction_score()
        
        # Использование функций
        feature_usage = await self.get_feature_usage()
        
        return {
            "active_sessions": active_sessions,
            "interaction_stats": interaction_stats,
            "satisfaction_score": satisfaction_score,
            "feature_usage": feature_usage,
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_active_sessions(self) -> int:
        """Получение количества активных сессий"""
        # Реализация зависит от системы управления сессиями
        return len(self.active_collectors.get("sessions", []))
        
    async def get_interaction_stats(self) -> dict:
        """Получение статистики взаимодействий"""
        # Статистика по взаимодействиям
        return {
            "total_interactions": 1000,
            "avg_session_duration": 300,  # секунды
            "interactions_per_hour": 50,
            "peak_usage_time": "14:00-16:00"
        }
```

## AnalyticsProcessor

### Обработка аналитики

```python
class AnalyticsProcessor:
    def __init__(self):
        self.analytics_rules = self.load_analytics_rules()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        
    def load_analytics_rules(self) -> dict:
        """Загрузка правил аналитики"""
        return {
            "performance_thresholds": {
                "response_time": 5.0,  # секунд
                "error_rate": 0.05,     # 5%
                "cpu_usage": 80.0,      # %
                "memory_usage": 85.0    # %
            },
            "ai_metrics_thresholds": {
                "token_usage_growth": 0.2,      # 20%
                "model_performance_drop": 0.1,  # 10%
                "emotion_stability": 0.8,       # 80%
                "goal_completion": 0.7         # 70%
            },
            "user_metrics_thresholds": {
                "satisfaction_score": 0.7,      # 70%
                "session_duration": 120,        # секунд
                "interaction_frequency": 5      # в час
            }
        }
        
    async def process_metrics(self, metrics: dict):
        """Обработка метрик"""
        # Анализ трендов
        await self.trend_analyzer.analyze_trends(metrics)
        
        # Обнаружение аномалий
        await self.anomaly_detector.detect_anomalies(metrics)
        
        # Генерация инсайтов
        insights = await self.generate_insights(metrics)
        
        # Отправка уведомлений
        await self.send_notifications(insights)
        
    async def generate_insights(self, metrics: dict) -> list:
        """Генерация инсайтов"""
        insights = []
        
        # Анализ производительности
        if metrics.get("system", {}).get("response_time", 0) > 5.0:
            insights.append({
                "type": "performance",
                "severity": "high",
                "message": "Высокое время ответа",
                "recommendation": "Оптимизировать производительность"
            })
            
        # Анализ использования токенов
        if metrics.get("ai", {}).get("token_usage", {}).get("total", 0) > 10000:
            insights.append({
                "type": "cost",
                "severity": "medium",
                "message": "Высокое использование токенов",
                "recommendation": "Проверить эффективность использования"
            })
            
        # Анализ удовлетворенности пользователей
        if metrics.get("user", {}).get("satisfaction_score", 1) < 0.7:
            insights.append({
                "type": "user",
                "severity": "high",
                "message": "Низкий уровень удовлетворенности",
                "recommendation": "Улучшить качество ответов"
            })
            
        return insights
```

## PerformanceMonitor

### Мониторинг производительности

```python
class PerformanceMonitor:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.performance_thresholds = {
            "response_time": 5.0,  # секунд
            "error_rate": 0.05,     # 5%
            "cpu_usage": 80.0,      # %
            "memory_usage": 85.0    # %
        }
        self.alerts = []
        
    async def monitor_performance(self):
        """Мониторинг производительности"""
        while True:
            try:
                # Получение метрик
                metrics = await self.get_current_metrics()
                
                # Проверка порогов
                await self.check_thresholds(metrics)
                
                # Анализ трендов
                await self.analyze_trends(metrics)
                
            except Exception as e:
                logger.error(f"Performance monitoring failed: {e}")
                
            await asyncio.sleep(30)  # Проверять каждые 30 секунд
            
    async def check_thresholds(self, metrics: dict):
        """Проверка пороговых значений"""
        alerts = []
        
        # Проверка времени ответа
        response_time = metrics.get("response_time", 0)
        if response_time > self.performance_thresholds["response_time"]:
            alerts.append({
                "type": "response_time",
                "value": response_time,
                "threshold": self.performance_thresholds["response_time"],
                "severity": "high"
            })
            
            {"x": m["timestamp"], "y": m["performance"]["response_time"]}
            for m in metrics
        ]
        chart_id = self.create_chart("line", response_time_data, {
            "title": "Response Time Trend",
            "x_label": "Time",
            "y_label": "Response Time (s)"
        })
        chart_ids.append(chart_id)
        
        # График error rate
        error_rate_data = [
            {"x": m["timestamp"], "y": m["performance"]["error_rate"]}
            for m in metrics
        ]
        chart_id = self.create_chart("line", error_rate_data, {
            "title": "Error Rate Trend",
            "x_label": "Time",
            "y_label": "Error Rate (%)"
        })
        chart_ids.append(chart_id)
        
        return chart_ids
```

### Форматы отчетов

```python
REPORT_FORMATS = {
    "json": "JSON format",
    "html": "HTML report",
    "pdf": "PDF document",
    "csv": "CSV data",
    "excel": "Excel spreadsheet"
}

def export_report(self, report: dict, format: str) -> bytes:
    """Экспорт отчета в указанный формат"""
    if format == "json":
        return json.dumps(report, indent=2, default=str).encode()
    elif format == "html":
        return self.generate_html_report(report)
    elif format == "pdf":
        return self.generate_pdf_report(report)
    elif format == "csv":
        return self.generate_csv_report(report)
    elif format == "excel":
        return self.generate_excel_report(report)
    else:
        raise ValueError(f"Unsupported format: {format}")
```

## PredictiveAnalyzer

### Предиктивный анализ

```python
class PredictiveAnalyzer:
    def __init__(self):
        self.models = {}
        self.forecast_horizon = 24  # часов
        
    async def predict_performance(self, metrics_history: list) -> dict:
        """Прогнозирование производительности"""
        # Подготовка данных
        data = self.prepare_performance_data(metrics_history)
        
        # Обучение модели
        model = await self.train_performance_model(data)
        
        # Прогнозирование
        forecast = await self.generate_forecast(model, self.forecast_horizon)
        
        return {
            "forecast": forecast,
            "confidence": self.calculate_confidence(forecast),
            "anomalies": await self.detect_future_anomalies(forecast)
        }
        
    def prepare_performance_data(self, metrics_history: list) -> pd.DataFrame:
        """Подготовка данных для анализа"""
        data = []
        for metrics in metrics_history:
            data.append({
                "timestamp": metrics["timestamp"],
                "response_time": metrics["performance"]["response_time"],
                "throughput": metrics["performance"]["throughput"],
                "error_rate": metrics["performance"]["error_rate"],
                "memory_usage": metrics["performance"]["memory_usage"]
            })
            
        return pd.DataFrame(data)
        
    async def train_performance_model(self, data: pd.DataFrame) -> object:
        """Обучение модели прогнозирования"""
        # Использование Prophet для временных рядов
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False
        )
        
        # Подготовка данных для Prophet
        df = data[["timestamp", "response_time"]].rename(columns={
            "timestamp": "ds",
            "response_time": "y"
        })
        
        model.fit(df)
        return model
```

### Прогнозирование аномалий

```python
async def detect_future_anomalies(self, forecast: dict) -> list:
    """Обнаружение будущих аномалий"""
    anomalies = []
    
    for i, prediction in enumerate(forecast["predictions"]):
        # Проверка на аномальные значения
        if self.is_anomalous(prediction):
            anomalies.append({
                "timestamp": forecast["timestamps"][i],
                "predicted_value": prediction,
                "severity": self.calculate_anomaly_severity(prediction),
                "description": self.generate_anomaly_description(prediction)
            })
            
    return anomalies
    
def is_anomalous(self, value: float) -> bool:
    """Проверка значения на аномальность"""
    # Использование статистических методов
    # Например, правило 3 сигм
    mean = self.get_historical_mean()
    std = self.get_historical_std()
    
    return abs(value - mean) > 3 * std
```

## API для аналитики

### Эндпоинты аналитики

```python
@app.get("/api/v1/analytics/metrics")
async def get_metrics(time_range: str = "1h"):
    """Получение метрик за указанный период"""
    end_time = datetime.now()
    
    if time_range == "1h":
        start_time = end_time - timedelta(hours=1)
    elif time_range == "24h":
        start_time = end_time - timedelta(hours=24)
    elif time_range == "7d":
        start_time = end_time - timedelta(days=7)
    else:
        start_time = end_time - timedelta(hours=1)
    
    metrics = await analytics_engine.get_metrics_in_range(start_time, end_time)
    return {"metrics": metrics}

@app.get("/api/v1/analytics/charts/{chart_id}")
async def get_chart(chart_id: str):
    """Получение данных для графика"""
    chart = data_visualizer.charts.get(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
        
    return chart

@app.post("/api/v1/analytics/reports")
async def generate_report(request: ReportRequest):
    """Генерация отчета"""
    if request.type == "performance":
        report = await report_generator.generate_performance_report(
            (request.start_time, request.end_time)
        )
    elif request.type == "emotion":
        report = await report_generator.generate_emotion_report(
            (request.start_time, request.end_time)
        )
    # ... другие типы отчетов
    
    return report
```

## Future улучшения

### Планы развития

1. **Real-time Analytics**
   - Обработка потоковых данных
   - Мгновенная визуализация
   - Live dashboards

2. **Advanced ML Models**
   - Deep learning для прогнозирования
   - Нейронные сети для анализа
   - Ensemble methods

3. **Custom Analytics**
   - Пользовательские метрики
   - Гибкие отчеты
   - Индивидуальные дашборды

4. **Integration with BI Tools**
   - Интеграция с Tableau
   - Поддержка Power BI
   - Экспорт в BI системы

5. **Predictive Maintenance**
   - Прогнозирование отказов
   - Проактивное обслуживание
   - Автоматическое предупреждение