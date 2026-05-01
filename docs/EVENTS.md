# Система Событий

Этот документ описывает систему событий в PAD+ AI.

## Обзор

Система событий обеспечивает:

- Централизованное управление событиями
- Асинхронную коммуникацию между компонентами
- Подписку и публикацию событий
- Обработку событий в реальном времени
- Интеграцию с WebSocket для клиентов

## Архитектура событий

### Компоненты

1. **EventBus** - Центральная шина событий
2. **EventPublisher** - Публикация событий
3. **EventSubscriber** - Подписка на события
4. **EventProcessor** - Обработка событий
5. **WebSocketBridge** - Мост для WebSocket

### Типы событий

```python
EVENT_TYPES = {
    # Системные события
    "system": {
        "startup": "Система запущена",
        "shutdown": "Система остановлена",
        "health_check": "Проверка здоровья системы",
        "error": "Системная ошибка"
    },
    
    # События пользователя
    "user": {
        "message_received": "Получено сообщение от пользователя",
        "session_started": "Начата сессия",
        "session_ended": "Завершена сессия",
        "preferences_changed": "Изменены настройки пользователя"
    },
    
    # События ИИ
    "ai": {
        "response_generated": "Сгенерирован ответ",
        "emotion_changed": "Изменено эмоциональное состояние",
        "goal_updated": "Обновлена цель",
        "memory_accessed": "Доступ к памяти"
    },
    
    # События безопасности
    "security": {
        "safety_violation": "Нарушение безопасности",
        "content_blocked": "Контент заблокирован",
        "threat_detected": "Обнаружена угроза",
        "anomaly_detected": "Обнаружена аномалия"
    },
    
    # События производительности
    "performance": {
        "slow_response": "Медленный ответ",
        "high_memory_usage": "Высокое использование памяти",
        "provider_error": "Ошибка провайдера",
        "cache_miss": "Промах кэша"
    }
}
```

## EventBus

### Центральная шина событий

```python
class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.event_history = []
        self.max_history_size = 10000
        self.event_processors = {}
        self.websocket_bridge = WebSocketBridge()
        
    def subscribe(self, event_type: str, callback: callable, priority: int = 0):
        """Подписка на событие"""
        subscriber = {
            "callback": callback,
            "priority": priority,
            "created_at": datetime.now()
        }
        
        self.subscribers[event_type].append(subscriber)
        
        # Сортировка по приоритету
        self.subscribers[event_type].sort(key=lambda x: x["priority"], reverse=True)
        
    def unsubscribe(self, event_type: str, callback: callable):
        """Отписка от события"""
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                sub for sub in self.subscribers[event_type] 
                if sub["callback"] != callback
            ]
            
    async def publish(self, event: Event):
        """Публикация события"""
        # 1. Сохранение в историю
        await self.store_event(event)
        
        # 2. Рассылка подписчикам
        await self.notify_subscribers(event)
        
        # 3. Обработка через WebSocket
        await self.websocket_bridge.broadcast_event(event)
        
        # 4. Логирование
        logger.info(f"Event published: {event.type} - {event.data}")
        
    async def store_event(self, event: Event):
        """Сохранение события в историю"""
        self.event_history.append(event)
        
        # Ограничение размера истории
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
            
    async def notify_subscribers(self, event: Event):
        """Оповещение подписчиков"""
        event_type = event.type
        
        # Поиск подходящих подписчиков
        matching_subscribers = []
        
        # Прямое соответствие типа
        if event_type in self.subscribers:
            matching_subscribers.extend(self.subscribers[event_type])
            
        # Поиск по wildcard
        for subscribed_type in self.subscribers:
            if self.matches_pattern(event_type, subscribed_type):
                matching_subscribers.extend(self.subscribers[subscribed_type])
                
        # Удаление дубликатов
        unique_subscribers = []
        seen_callbacks = set()
        
        for subscriber in matching_subscribers:
            callback_id = id(subscriber["callback"])
            if callback_id not in seen_callbacks:
                unique_subscribers.append(subscriber)
                seen_callbacks.add(callback_id)
                
        # Сортировка по приоритету
        unique_subscribers.sort(key=lambda x: x["priority"], reverse=True)
        
        # Уведомление подписчиков
        for subscriber in unique_subscribers:
            try:
                await subscriber["callback"](event)
            except Exception as e:
                logger.error(f"Subscriber callback failed: {e}")
```

### Сопоставление паттернов

```python
def matches_pattern(self, event_type: str, pattern: str) -> bool:
    """Проверка соответствия паттерну"""
    # Поддержка wildcard
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return event_type.startswith(prefix)
    else:
        return event_type == pattern
        
    async def get_event_history(self, event_type: str = None, limit: int = 100) -> list:
        """Получение истории событий"""
        if event_type:
            history = [event for event in self.event_history if event.type == event_type]
        else:
            history = self.event_history
            
        # Сортировка по времени (новые первыми)
        history.sort(key=lambda x: x.timestamp, reverse=True)
        
        return history[:limit]
```

## EventPublisher

### Публикация событий

```python
class EventPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.component_name = ""
        
    def set_component_name(self, name: str):
        """Установка имени компонента"""
        self.component_name = name
        
    async def publish_event(self, event_type: str, data: dict, priority: int = 0):
        """Публикация события"""
        event = Event(
            type=event_type,
            data=data,
            source=self.component_name,
            timestamp=datetime.now(),
            priority=priority
        )
        
        await self.event_bus.publish(event)
        
    async def publish_system_event(self, event_type: str, message: str):
        """Публикация системного события"""
        await self.publish_event(
            event_type=f"system.{event_type}",
            data={
                "message": message,
                "component": self.component_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    async def publish_user_event(self, event_type: str, user_id: str, data: dict):
        """Публикация пользовательского события"""
        await self.publish_event(
            event_type=f"user.{event_type}",
            data={
                "user_id": user_id,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    async def publish_ai_event(self, event_type: str, ai_data: dict):
        """Публикация AI события"""
        await self.publish_event(
            event_type=f"ai.{event_type}",
            data={
                "ai_data": ai_data,
                "timestamp": datetime.now().isoformat()
            }
        )
```

### Специализированные публикаторы

```python
class SafetyEventPublisher(EventPublisher):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.set_component_name("safety")
        
    async def publish_safety_violation(self, violation_type: str, details: dict):
        """Публикация нарушения безопасности"""
        await self.publish_event(
            event_type="security.safety_violation",
            data={
                "violation_type": violation_type,
                "details": details,
                "severity": self.calculate_severity(violation_type, details)
            }
        )
        
    def calculate_severity(self, violation_type: str, details: dict) -> str:
        """Расчет уровня серьезности нарушения"""
        risk_score = details.get("risk_score", 0.0)
        
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"
            
class PerformanceEventPublisher(EventPublisher):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.set_component_name("performance")
        
    async def publish_slow_response(self, response_time: float, request_data: dict):
        """Публикация медленного ответа"""
        await self.publish_event(
            event_type="performance.slow_response",
            data={
                "response_time": response_time,
                "request_data": request_data,
                "threshold": 5.0  # секунд
            }
        )
```

## EventSubscriber

### Подписка на события

```python
class EventSubscriber:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.subscriptions = []
        
    def subscribe_to_event(self, event_type: str, callback: callable, priority: int = 0):
        """Подписка на конкретное событие"""
        self.event_bus.subscribe(event_type, callback, priority)
        self.subscriptions.append({
            "event_type": event_type,
            "callback": callback,
            "priority": priority
        })
        
    def subscribe_to_pattern(self, pattern: str, callback: callable, priority: int = 0):
        """Подписка на события по паттерну"""
        self.event_bus.subscribe(pattern, callback, priority)
        self.subscriptions.append({
            "event_type": pattern,
            "callback": callback,
            "priority": priority,
            "pattern": True
        })
        
    def unsubscribe_from_event(self, event_type: str, callback: callable):
        """Отписка от события"""
        self.event_bus.unsubscribe(event_type, callback)
        
        # Удаление из списка подписок
        self.subscriptions = [
            sub for sub in self.subscriptions 
            if not (sub["event_type"] == event_type and sub["callback"] == callback)
        ]
        
    def unsubscribe_all(self):
        """Отписка от всех событий"""
        for subscription in self.subscriptions:
            self.event_bus.unsubscribe(
                subscription["event_type"], 
                subscription["callback"]
            )
        self.subscriptions = []
```

### Обработчики событий

```python
class SystemEventHandler:
    def __init__(self, event_bus: EventBus):
        self.subscriber = EventSubscriber(event_bus)
        self.setup_subscriptions()
        
    def setup_subscriptions(self):
        """Настройка подписок на системные события"""
        self.subscriber.subscribe_to_event("system.startup", self.handle_startup)
        self.subscriber.subscribe_to_event("system.shutdown", self.handle_shutdown)
        self.subscriber.subscribe_to_event("system.error", self.handle_error)
        self.subscriber.subscribe_to_pattern("performance.*", self.handle_performance_event)
        
    async def handle_startup(self, event: Event):
        """Обработка события запуска системы"""
        logger.info("System startup event received")
        # Логика обработки запуска
        
    async def handle_shutdown(self, event: Event):
        """Обработка события остановки системы"""
        logger.info("System shutdown event received")
        # Логика обработки остановки
        
    async def handle_error(self, event: Event):
        """Обработка системной ошибки"""
        error_data = event.data
        logger.error(f"System error: {error_data}")
        # Логика обработки ошибки
        
    async def handle_performance_event(self, event: Event):
        """Обработка событий производительности"""
        event_type = event.type
        data = event.data
        
        if event_type == "performance.slow_response":
            await self.handle_slow_response(data)
        elif event_type == "performance.high_memory_usage":
            await self.handle_high_memory_usage(data)
            
    async def handle_slow_response(self, data: dict):
        """Обработка медленного ответа"""
        response_time = data.get("response_time", 0.0)
        logger.warning(f"Slow response detected: {response_time} seconds")
        # Логика обработки медленного ответа
        
    async def handle_high_memory_usage(self, data: dict):
        """Обработка высокого использования памяти"""
        memory_usage = data.get("memory_usage", 0.0)
        logger.warning(f"High memory usage: {memory_usage}%")
        # Логика обработки высокого использования памяти
```

## WebSocketBridge

### Мост для WebSocket

```python
class WebSocketBridge:
    def __init__(self):
        self.connected_clients = set()
        self.client_subscriptions = {}
        
    async def broadcast_event(self, event: Event):
        """Трансляция события клиентам"""
        # Фильтрация клиентов по подпискам
        target_clients = self.get_target_clients(event)
        
        # Отправка события клиентам
        for client in target_clients:
            try:
                await self.send_event_to_client(client, event)
            except Exception as e:
                logger.error(f"Failed to send event to client: {e}")
                # Удаление недоступного клиента
                await self.remove_client(client)
                
    def get_target_clients(self, event: Event) -> set:
        """Получение целевых клиентов для события"""
        target_clients = set()
        
        for client, subscriptions in self.client_subscriptions.items():
            if self.client_subscribed_to_event(client, event):
                target_clients.add(client)
                
        return target_clients
        
    def client_subscribed_to_event(self, client: WebSocket, event: Event) -> bool:
        """Проверка подписки клиента на событие"""
        subscriptions = self.client_subscriptions.get(client, [])
        
        for subscription in subscriptions:
            if self.matches_subscription(event, subscription):
                return True
                
        return False
        
    def matches_subscription(self, event: Event, subscription: dict) -> bool:
        """Проверка соответствия события подписке"""
        event_type = event.type
        subscription_type = subscription.get("event_type", "")
        
        # Прямое соответствие
        if event_type == subscription_type:
            return True
            
        # Соответствие по wildcard
        if subscription_type.endswith("*"):
            prefix = subscription_type[:-1]
            return event_type.startswith(prefix)
            
        return False
        
    async def send_event_to_client(self, client: WebSocket, event: Event):
        """Отправка события клиенту"""
        event_data = {
            "type": "event",
            "event_type": event.type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source
        }
        
        await client.send_text(json.dumps(event_data, ensure_ascii=False))
```

### Управление клиентами

```python
async def add_client(self, client: WebSocket, subscriptions: list = None):
    """Добавление клиента"""
        self.connected_clients.add(client)
        self.client_subscriptions[client] = subscriptions or []
        
    async def remove_client(self, client: WebSocket):
        """Удаление клиента"""
        self.connected_clients.discard(client)
        if client in self.client_subscriptions:
            del self.client_subscriptions[client]
            
    async def update_client_subscriptions(self, client: WebSocket, subscriptions: list):
        """Обновление подписок клиента"""
        if client in self.client_subscriptions:
            self.client_subscriptions[client] = subscriptions
            
    def get_client_count(self) -> int:
        """Получение количества подключенных клиентов"""
        return len(self.connected_clients)
        
    def get_subscription_stats(self) -> dict:
        """Получение статистики по подпискам"""
        stats = defaultdict(int)
        
        for subscriptions in self.client_subscriptions.values():
            for subscription in subscriptions:
                event_type = subscription.get("event_type", "unknown")
                stats[event_type] += 1
                
        return dict(stats)
```

## Future улучшения

### Планы развития

1. **Event Streaming**
   - Real-time event streaming
   - Event persistence and replay
   - Event stream processing

2. **Event Analytics**
   - Event pattern analysis
   - Performance monitoring
   - Usage analytics

3. **Event Orchestration**
   - Complex event processing
   - Event correlation
   - Workflow automation

4. **Event Security**
   - Event authentication
   - Event encryption
   - Access control for events

5. **Event Scalability**
   - Distributed event bus
   - Event load balancing
   - High-throughput event processing