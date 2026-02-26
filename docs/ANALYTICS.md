# Система Аналитики

Этот документ описывает систему аналитики в PAD+ AI.

## Обзор

Система аналитики обеспечивает:

- Сбор и анализ метрик производительности
- Визуализацию данных в реальном времени
- Прогнозирование и предиктивную аналитику
- Отчеты и дашборды
- Мониторинг состояния системы

## Архитектура аналитики

### Компоненты

1. **MetricsCollector** - Сбор метрик
2. **AnalyticsEngine** - Аналитический движок
3. **DataVisualizer** - Визуализация данных
4. **ReportGenerator** - Генерация отчетов
5. **PredictiveAnalyzer** - Предиктивный анализ

### Типы метрик

```python
METRIC_TYPES = {
    # Производительность
    "response_time": "Время ответа",
    "throughput": "Пропускная способность",
    "error_rate": "Процент ошибок",
    "memory_usage": "Использование памяти",
    
    # Эмоциональные метрики
    "emotion_stability": "Эмоциональная стабильность",
    "mood_trends": "Тренды настроения",
    "engagement_level": "Уровень вовлеченности",
    
    # Автономия
    "task_completion_rate": "Процент завершенных задач",
    "goal_achievement": "Достижение целей",
    "learning_progress": "Прогресс обучения",
    
    # Память
    "memory_utilization": "Использование памяти",
    "recall_accuracy": "Точность воспроизведения",
    "knowledge_growth": "Рост знаний",
    
    # Безопасность
    "security_incidents": "Инциденты безопасности",
    "blocked_requests": "Заблокированные запросы",
    "verification_success": "Успешность верификации"
}
```

## MetricsCollector (core/analytics.py)

### Сбор метрик

```python
class MetricsCollector:
    def __init__(self):
        self.metrics = {}
        self.collection_interval = 60  # секунд
        self.running = False
        
    async def start(self):
        """Запуск сбора метрик"""
        self.running = True
        asyncio.create_task(self.collect_metrics_loop())
        
    async def stop(self):
        """Остановка сбора метрик"""
        self.running = False
        
    async def collect_metrics_loop(self):
        """Цикл сбора метрик"""
        while self.running:
            # Сбор всех типов метрик
            performance_metrics = await self.collect_performance_metrics()
            emotion_metrics = await self.collect_emotion_metrics()
            autonomy_metrics = await self.collect_autonomy_metrics()
            memory_metrics = await self.collect_memory_metrics()
            safety_metrics = await self.collect_safety_metrics()
            
            # Сохранение метрик
            timestamp = datetime.now()
            metrics_data = {
                "timestamp": timestamp,
                "performance": performance_metrics,
                "emotion": emotion_metrics,
                "autonomy": autonomy_metrics,
                "memory": memory_metrics,
                "safety": safety_metrics
            }
            
            await self.store_metrics(metrics_data)
            
            # Рассылка через WebSocket
            await ws_manager.broadcast({
                "type": "analytics_update",
                "data": metrics_data
            })
            
            await asyncio.sleep(self.collection_interval)
            
    async def collect_performance_metrics(self) -> dict:
        """Сбор метрик производительности"""
        return {
            "response_time": await self.get_response_time(),
            "throughput": await self.get_throughput(),
            "error_rate": await self.get_error_rate(),
            "memory_usage": await self.get_memory_usage(),
            "cpu_usage": await self.get_cpu_usage()
        }
        
    async def collect_emotion_metrics(self) -> dict:
        """Сбор эмоциональных метрик"""
        emotion_state = emotion_manager.get_state()
        
        return {
            "current_emotions": emotion_state,
            "emotion_stability": await self.calculate_emotion_stability(),
            "mood_trends": await self.get_mood_trends(),
            "engagement_level": await self.calculate_engagement()
        }
```

### Специализированные метрики

```python
async def collect_autonomy_metrics(self) -> dict:
    """Сбор метрик автономии"""
    autonomy_status = await autonomy_manager.get_status()
    
    return {
        "task_completion_rate": autonomy_status["completed_tasks"] / max(1, autonomy_status["total_tasks"]),
        "goal_achievement": await self.get_goal_achievement(),
        "learning_progress": await self.get_learning_progress(),
        "autonomy_level": autonomy_manager.autonomy_level,
        "active_tasks": len(autonomy_manager.planner.tasks)
    }
    
async def collect_memory_metrics(self) -> dict:
    """Сбор метрик памяти"""
    rag_stats = await rag_system.get_statistics()
    facts_stats = await facts_manager.get_statistics()
    knowledge_stats = await knowledge_graph.get_statistics()
    
    return {
        "memory_utilization": rag_stats["total_dialogs"],
        "recall_accuracy": await self.calculate_recall_accuracy(),
        "knowledge_growth": knowledge_stats["total_entities"],
        "fact_confidence": facts_stats["avg_confidence"],
        "memory_efficiency": await self.calculate_memory_efficiency()
    }
    
async def collect_safety_metrics(self) -> dict:
    """Сбор метрик безопасности"""
    safety_stats = await safety_layer.get_statistics()
    
    return {
        "security_incidents": safety_stats["violations"],
        "blocked_requests": safety_stats["blocked_count"],
        "verification_success": safety_stats["verification_rate"],
        "false_positive_rate": safety_stats["false_positives"],
        "response_time": safety_stats["avg_check_time"]
    }
```

## AnalyticsEngine

### Аналитический движок

```python
class AnalyticsEngine:
    def __init__(self):
        self.analyzers = {}
        self.trend_analyzer = TrendAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        
    async def analyze_metrics(self, metrics_data: dict) -> dict:
        """Анализ метрик"""
        analysis = {
            "performance_analysis": await self.analyze_performance(metrics_data["performance"]),
            "emotion_analysis": await self.analyze_emotions(metrics_data["emotion"]),
            "autonomy_analysis": await self.analyze_autonomy(metrics_data["autonomy"]),
            "memory_analysis": await self.analyze_memory(metrics_data["memory"]),
            "safety_analysis": await self.analyze_safety(metrics_data["safety"]),
            "trends": await self.trend_analyzer.analyze_trends(metrics_data),
            "correlations": await self.correlation_analyzer.find_correlations(metrics_data),
            "anomalies": await self.anomaly_detector.detect_anomalies(metrics_data)
        }
        
        return analysis
        
    async def analyze_performance(self, performance_data: dict) -> dict:
        """Анализ производительности"""
        return {
            "response_time_analysis": self.analyze_response_time(performance_data["response_time"]),
            "throughput_analysis": self.analyze_throughput(performance_data["throughput"]),
            "error_rate_analysis": self.analyze_error_rate(performance_data["error_rate"]),
            "resource_utilization": self.analyze_resource_utilization(performance_data)
        }
        
    def analyze_response_time(self, response_time: float) -> dict:
        """Анализ времени ответа"""
        if response_time < 1.0:
            status = "excellent"
        elif response_time < 3.0:
            status = "good"
        elif response_time < 5.0:
            status = "acceptable"
        else:
            status = "poor"
            
        return {
            "value": response_time,
            "status": status,
            "recommendations": self.get_response_time_recommendations(response_time)
        }
```

### Анализ эмоций

```python
async def analyze_emotions(self, emotion_data: dict) -> dict:
    """Анализ эмоциональных метрик"""
    emotions = emotion_data["current_emotions"]
    
    # Анализ стабильности
    stability = self.calculate_emotion_stability(emotions)
    
    # Анализ баланса
    balance = self.analyze_emotion_balance(emotions)
    
    # Анализ трендов
    trends = await self.trend_analyzer.analyze_emotion_trends(emotions)
    
    return {
        "stability": stability,
        "balance": balance,
        "trends": trends,
        "recommendations": self.get_emotion_recommendations(emotions)
    }
    
def calculate_emotion_stability(self, emotions: dict) -> float:
    """Расчет эмоциональной стабильности"""
    # Расчет стандартного отклонения от нормальных значений
    normal_values = {
        "удовольствие": 0.5,
        "возбуждение": 0.3,
        "доминирование": 0.5,
        "любопытство": 0.5,
        "уверенность": 0.5,
        "социальная_связь": 0.5
    }
    
    deviations = []
    for emotion, value in emotions.items():
        if emotion in normal_values:
            deviation = abs(value - normal_values[emotion])
            deviations.append(deviation)
    
    stability = 1.0 - (sum(deviations) / len(deviations))
    return max(0.0, min(1.0, stability))
```

## DataVisualizer

### Визуализация данных

```python
class DataVisualizer:
    def __init__(self):
        self.charts = {}
        self.dashboards = {}
        
    def create_chart(self, chart_type: str, data: dict, options: dict = None) -> str:
        """Создание графика"""
        chart_id = str(uuid.uuid4())
        
        chart = {
            "id": chart_id,
            "type": chart_type,
            "data": data,
            "options": options or {},
            "created_at": datetime.now()
        }
        
        self.charts[chart_id] = chart
        return chart_id
        
    def create_dashboard(self, dashboard_name: str, charts: list) -> str:
        """Создание дашборда"""
        dashboard_id = str(uuid.uuid4())
        
        dashboard = {
            "id": dashboard_id,
            "name": dashboard_name,
            "charts": charts,
            "layout": self.calculate_layout(charts),
            "created_at": datetime.now()
        }
        
        self.dashboards[dashboard_id] = dashboard
        return dashboard_id
        
    def calculate_layout(self, charts: list) -> dict:
        """Расчет расположения графиков на дашборде"""
        # Алгоритм автоматического расположения
        layout = {}
        row = 0
        col = 0
        
        for chart_id in charts:
            layout[chart_id] = {
                "row": row,
                "col": col,
                "width": 4,
                "height": 3
            }
            
            col += 4
            if col >= 12:
                col = 0
                row += 3
                
        return layout
```

### Типы графиков

```python
CHART_TYPES = {
    "line": "Линейный график",
    "bar": "Столбчатая диаграмма",
    "pie": "Круговая диаграмма",
    "scatter": "Точечная диаграмма",
    "heatmap": "Тепловая карта",
    "gauge": "Индикатор",
    "area": "Область",
    "bubble": "Пузырьковая диаграмма"
}

def generate_chart_data(self, chart_type: str, metrics: list) -> dict:
    """Генерация данных для графика"""
    if chart_type == "line":
        return self.generate_line_chart_data(metrics)
    elif chart_type == "bar":
        return self.generate_bar_chart_data(metrics)
    elif chart_type == "pie":
        return self.generate_pie_chart_data(metrics)
    # ... другие типы графиков
```

## ReportGenerator

### Генерация отчетов

```python
class ReportGenerator:
    def __init__(self):
        self.report_templates = {}
        self.report_history = []
        
    def generate_performance_report(self, time_range: tuple) -> dict:
        """Генерация отчета по производительности"""
        metrics = await self.get_metrics_in_range(time_range)
        
        report = {
            "title": "Performance Report",
            "period": time_range,
            "generated_at": datetime.now(),
            "summary": self.generate_performance_summary(metrics),
            "details": self.generate_performance_details(metrics),
            "charts": self.generate_performance_charts(metrics),
            "recommendations": self.generate_performance_recommendations(metrics)
        }
        
        self.report_history.append(report)
        return report
        
    def generate_performance_summary(self, metrics: list) -> dict:
        """Генерация сводки по производительности"""
        response_times = [m["performance"]["response_time"] for m in metrics]
        error_rates = [m["performance"]["error_rate"] for m in metrics]
        throughputs = [m["performance"]["throughput"] for m in metrics]
        
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "avg_error_rate": sum(error_rates) / len(error_rates),
            "max_error_rate": max(error_rates),
            "avg_throughput": sum(throughputs) / len(throughputs),
            "total_requests": sum(m["performance"]["total_requests"] for m in metrics)
        }
        
    def generate_performance_charts(self, metrics: list) -> list:
        """Генерация графиков производительности"""
        chart_ids = []
        
        # График времени ответа
        response_time_data = [
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