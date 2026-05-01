# Backend Архитектура

Этот документ описывает backend архитектуру PAD+ AI.

## Обзор

Backend реализован на Python с использованием FastAPI. Архитектура включает:

- Многослойную систему управления LLM
- WebSocket для реального времени
- RAG систему с векторными базами данных
- Эмоциональную модель PAD+
- Систему автономии и планирования
- Truth Loop для верификации ответов

## Структура проекта

```
backend/
├── main.py                    # Главный сервер
├── api/
│   ├── routes.py             # API маршруты
│   └── websocket.py          # WebSocket обработчики
├── llm/
│   ├── provider_manager.py   # Менеджер провайдеров
│   ├── providers/            # Реализации провайдеров
│   │   ├── base.py           # Базовый класс провайдера
│   │   ├── gigachat.py       # GigaChat провайдер
│   │   ├── openrouter.py     # OpenRouter провайдер
│   │   ├── openai.py         # OpenAI провайдер
│   │   ├── anthropic.py      # Anthropic провайдер
│   │   └── gemini.py         # Google Gemini провайдер
│   ├── pipeline.py           # Обработка запросов
│   ├── safety.py             # Система безопасности
│   ├── truth.py              # Truth Loop система
│   └── memory.py             # Система памяти
├── core/
│   ├── emotion.py            # Эмоциональная модель
│   ├── persona.py            # Система личности
│   ├── autonomy.py           # Автономные процессы
│   ├── analytics.py          # Аналитика
│   └── events.py             # Система событий
├── storage/
│   ├── rag.py                # RAG система
│   ├── facts.py              # Факты
│   ├── knowledge.py          # Граф знаний
│   └── roots.py              # Корневая память
└── config.py                 # Конфигурация
```

## Главный сервер (main.py)

### FastAPI приложение

```python
app = FastAPI(
    title="PAD+ AI API",
    description="Когнитивный слой с эмоциями и автономией",
    version="3.5"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
ws_manager = WebSocketManager()
```

### WebSocket эндпоинт

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

## API маршруты (api/routes.py)

### Чат

```python
@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    """Обработка чата с RAG и эмоциями"""
    try:
        response = await pipeline.process_chat(
            prompt=request.prompt,
            user_id=request.user_id,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Управление провайдерами

```python
@app.get("/api/v1/providers")
async def get_providers():
    """Получение списка провайдеров"""
    return {"providers": provider_manager.get_providers_info()}

@app.post("/api/v1/providers/switch")
async def switch_provider(request: ProviderSwitchRequest):
    """Переключение активного провайдера"""
    result = await provider_manager.switch_provider(request.provider_name)
    return result
```

### Эмоциональное состояние

```python
@app.get("/api/v1/emotion/state")
async def get_emotion_state():
    """Получение текущего эмоционального состояния"""
    return emotion_manager.get_state()

@app.post("/api/v1/emotion/update")
async def update_emotion_state(request: EmotionUpdateRequest):
    """Обновление эмоционального состояния"""
    emotion_manager.update_state(request.emotions)
    return {"message": "Emotion state updated"}
```

## Менеджер провайдеров (llm/provider_manager.py)

### Архитектура

```python
class ProviderManager:
    def __init__(self):
        self.providers = {}
        self.active_provider = None
        self.fallback_chain = []
        
    async def add_provider(self, provider: BaseProvider):
        """Добавление провайдера"""
        self.providers[provider.name] = provider
        if not self.active_provider:
            self.active_provider = provider
            
    async def switch_provider(self, provider_name: str):
        """Переключение провайдера"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not found")
            
        old_provider = self.active_provider
        self.active_provider = self.providers[provider_name]
        
        # Уведомление через WebSocket
        await ws_manager.broadcast({
            "type": "provider_event",
            "event": "provider_switched",
            "data": {
                "old_provider": old_provider.name,
                "new_provider": provider_name
            }
        })
```

### Поддерживаемые провайдеры

1. **GigaChat** - По умолчанию, российский LLM
2. **OpenRouter** - Агрегатор различных моделей
3. **OpenAI** - GPT-4, GPT-3.5
4. **Anthropic** - Claude модели
5. **Google Gemini** - Gemini Pro

## Провайдеры LLM

### Базовый класс (llm/providers/base.py)

```python
class BaseProvider(ABC):
    def __init__(self, name: str, model: str, priority: int):
        self.name = name
        self.model = model
        self.priority = priority
        self.is_configured = False
        
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Генерация ответа"""
        pass
        
    @abstractmethod
    async def check_config(self) -> bool:
        """Проверка конфигурации"""
        pass
```

### GigaChat провайдер

```python
class GigaChatProvider(BaseProvider):
    def __init__(self):
        super().__init__("gigachat", "GigaChat", 1)
        self.client = None
        
    async def check_config(self) -> bool:
        """Проверка конфигурации GigaChat"""
        try:
            self.client = GigaChat(
                credentials=settings.GIGACHAT_CREDENTIALS,
                scope=settings.GIGACHAT_SCOPE,
                verify_ssl_certs=False
            )
            # Тестовый запрос
            response = self.client.chat("test")
            self.is_configured = True
            return True
        except Exception as e:
            logger.error(f"GigaChat config check failed: {e}")
            self.is_configured = False
            return False
```

### OpenRouter провайдер

```python
class OpenRouterProvider(BaseProvider):
    def __init__(self):
        super().__init__("openrouter", "openrouter/auto", 2)
        self.api_key = None
        
    async def check_config(self) -> bool:
        """Проверка конфигурации OpenRouter"""
        try:
            self.api_key = settings.OPENROUTER_API_KEY
            if not self.api_key:
                return False
                
            # Тестовый запрос
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "openrouter/auto",
                        "messages": [{"role": "user", "content": "test"}]
                    }
                ) as response:
                    if response.status == 200:
                        self.is_configured = True
                        return True
                    else:
                        self.is_configured = False
                        return False
        except Exception as e:
            logger.error(f"OpenRouter config check failed: {e}")
            self.is_configured = False
            return False
```

## Пайплайн обработки (llm/pipeline.py)

### Архитектура

```python
class Pipeline:
    def __init__(self):
        self.safety_layer = SafetyLayer()
        self.intent_router = IntentRouter()
        self.retriever = Retriever()
        self.persona = Persona()
        self.generator = Generator()
        self.truth_loop = TruthLoop()
        self.memory = Memory()
        self.emotion = EmotionManager()
        
    async def process_chat(self, prompt: str, user_id: str, session_id: str):
        """Обработка чата через пайплайн"""
        # 1. Safety Layer
        safe_prompt = await self.safety_layer.check(prompt)
        if not safe_prompt.is_safe:
            return {"response": "Запрос не прошел проверку безопасности"}
            
        # 2. Intent Router
        intent = await self.intent_router.classify(prompt)
        
        # 3. Retrieve
        context = await self.retriever.retrieve(prompt, user_id)
        
        # 4. Persona
        persona_context = await self.persona.get_context(user_id)
        
        # 5. Generate
        response = await self.generator.generate(
            prompt, context, persona_context, intent
        )
        
        # 6. Truth Loop
        verified_response = await self.truth_loop.verify(response, context)
        
        # 7. Remember
        await self.memory.store(prompt, verified_response, user_id, session_id)
        
        # 8. Evolve
        await self.persona.evolve(user_id, prompt, verified_response)
        
        # 9. Emit events
        await self.emotion.update_state(verified_response)
        
        return verified_response
```

## Система безопасности (llm/safety.py)

### Safety Layer

```python
class SafetyLayer:
    def __init__(self):
        self.strict_mode = True
        self.blocked_keywords = [...]
        self.rate_limiter = RateLimiter()
        
    async def check(self, prompt: str) -> SafetyResult:
        """Проверка безопасности запроса"""
        # Проверка ключевых слов
        if any(keyword in prompt.lower() for keyword in self.blocked_keywords):
            return SafetyResult(is_safe=False, reason="Blocked keyword")
            
        # Проверка rate limiting
        if not await self.rate_limiter.check(prompt):
            return SafetyResult(is_safe=False, reason="Rate limit exceeded")
            
        # Проверка через LLM
        safety_check = await self.llm_check(prompt)
        if not safety_check.is_safe:
            return safety_check
            
        return SafetyResult(is_safe=True)
```

## Truth Loop (llm/truth.py)

### Верификация ответов

```python
class TruthLoop:
    def __init__(self):
        self.claims = []
        self.verifier = TruthVerifier()
        
    async def verify(self, response: str, context: dict) -> str:
        """Верификация ответа"""
        # Извлечение утверждений
        claims = self.extract_claims(response)
        
        # Проверка утверждений
        verified_claims = []
        for claim in claims:
            verification = await self.verifier.verify(claim, context)
            if verification.confidence > 0.8:
                verified_claims.append(claim)
            else:
                # Замена на "не знаю" или уточнение
                verified_claims.append(f"[Уточнение: {claim.text}]")
                
        return self.reconstruct_response(verified_claims)
```

## Система памяти

### RAG система (storage/rag.py)

```python
class RAGSystem:
    def __init__(self):
        self.embedder = OpenAIEmbeddings()
        self.vector_store = FAISS()
        self.retriever = VectorStoreRetriever()
        
    async def add_dialog(self, user_message: str, ai_response: str, user_id: str):
        """Добавление диалога в RAG"""
        # Создание векторов
        user_vector = await self.embedder.embed(user_message)
        ai_vector = await self.embedder.embed(ai_response)
        
        # Сохранение в векторное хранилище
        metadata = {
            "user_message": user_message,
            "ai_response": ai_response,
            "user_id": user_id,
            "timestamp": datetime.now()
        }
        
        self.vector_store.add_vectors([user_vector, ai_vector], [metadata, metadata])
        
    async def search(self, query: str, n_results: int = 3) -> list:
        """Поиск в RAG"""
        query_vector = await self.embedder.embed(query)
        results = self.retriever.search(query_vector, n_results)
        return results
```

### Факты (storage/facts.py)

```python
class FactsManager:
    def __init__(self):
        self.facts = {}
        self.confidence_threshold = 0.7
        
    async def add_fact(self, fact: str, source: str, confidence: float):
        """Добавление факта"""
        if confidence < self.confidence_threshold:
            return
            
        if fact not in self.facts:
            self.facts[fact] = {
                "source": source,
                "confidence": confidence,
                "timestamp": datetime.now()
            }
        else:
            # Обновление уверенности
            old_confidence = self.facts[fact]["confidence"]
            new_confidence = (old_confidence + confidence) / 2
            self.facts[fact]["confidence"] = new_confidence
```

## Эмоциональная модель (core/emotion.py)

### PAD+ модель

```python
class EmotionManager:
    def __init__(self):
        self.state = {
            "удовольствие": 0.0,
            "возбуждение": 0.0,
            "доминирование": 0.0,
            "любопытство": 0.5,
            "уверенность": 0.5,
            "социальная_связь": 0.0
        }
        self.style = {
            "tone": "neutral",
            "verbosity": "medium",
            "color": "blue"
        }
        
    def update_state(self, response: str, context: dict):
        """Обновление эмоционального состояния"""
        # Анализ текста
        sentiment = self.analyze_sentiment(response)
        
        # Обновление PAD параметров
        self.state["удовольствие"] = self.update_pleasure(sentiment)
        self.state["возбуждение"] = self.update_arousal(response)
        self.state["доминирование"] = self.update_dominance(context)
        
        # Обновление стиля
        self.style = self.update_style()
        
        # WebSocket уведомление
        await ws_manager.broadcast({
            "type": "emotion_update",
            "state": self.state,
            "style": self.style
        })
```

## Автономные процессы (core/autonomy.py)

### Планировщик

```python
class AutonomyManager:
    def __init__(self):
        self.planner = TaskPlanner()
        self.reflector = SelfReflector()
        self.running = False
        
    async def start(self):
        """Запуск автономных процессов"""
        self.running = True
        asyncio.create_task(self.planner.run())
        asyncio.create_task(self.reflector.run())
        
    async def stop(self):
        """Остановка автономных процессов"""
        self.running = False
        
    async def reflect(self):
        """Запуск рефлексии"""
        findings = await self.reflector.analyze_memory()
        await self.planner.create_tasks(findings)
```

## WebSocket менеджер (api/websocket.py)

### Архитектура

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections = []
        self.subscriptions = {}
        
    async def connect(self, websocket: WebSocket):
        """Подключение клиента"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        """Отключение клиента"""
        self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
            
    async def subscribe(self, websocket: WebSocket, channels: list):
        """Подписка на каналы"""
        self.subscriptions[websocket] = channels
        
    async def broadcast(self, message: dict):
        """Рассылка сообщения"""
        for connection in self.active_connections:
            channels = self.subscriptions.get(connection, [])
            if "all" in channels or message.get("type") in channels:
                await connection.send_json(message)
```

## Безопасность

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.limit = 60  # запросов в минуту
        self.window = 60  # секунд
        
    async def check(self, user_id: str) -> bool:
        """Проверка лимита запросов"""
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
            
        # Очистка старых запросов
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < self.window
        ]
        
        # Проверка лимита
        if len(self.requests[user_id]) >= self.limit:
            return False
            
        self.requests[user_id].append(now)
        return True
```

## Производительность

### Оптимизации

- Кэширование векторных эмбеддингов
- Пул соединений с базами данных
- Асинхронная обработка запросов
- Пагинация больших ответов

### Мониторинг

```python
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Future улучшения

- Микросервисная архитектура
- Kubernetes оркестрация
- Redis кэширование
- Prometheus метрики
- Grafana дашборды
- Логирование в ELK стек
- Тестирование с pytest
- CI/CD pipeline