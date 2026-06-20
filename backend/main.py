"""
PAD+ AI v4.0 — Главный модуль

Когнитивный слой, добавляющий эмоции и самосознание любому LLM.
PAD+ = Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (в корне проекта) ДО всех импортов
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Добавляем корень проекта в sys.path (нужно для абсолютных импортов вида backend.*)
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Настройка логирования (единожды)
# Принудительно UTF-8 для stdout/stderr (нужно на Render/Linux где LANG=C)
import io
if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger("padplus")

# Импорт ядра
sys.path.insert(0, str(Path(__file__).parent))

from core.anti_directive import ANTI_DIRECTIVE, check_integrity
from core.cache_manager import get_cache_manager
from core.monitoring import get_monitoring_system
from core.dependencies import register_dependencies
from api import routes

# Импортируем core модули ПОСЛЕ загрузки .env
from core.supabase_client import get_supabase, check_database_connection
from core.auth_manager import get_current_user_safe

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # === STARTUP ===
    logger.info("🧠 PAD+ AI v4.0 запускается...")
    start_time = time.time()
    
    # Регистрация зависимостей (Вторая очередь улучшений)
    logger.info("📦 Регистрация зависимостей...")
    register_dependencies()
    logger.info(f"✅ Dependency Injection инициализирован ({time.time()-start_time:.2f}s)")

    # Проверка целостности ANTI_DIRECTIVE
    logger.info("🔒 Проверка ANTI_DIRECTIVE...")
    if not check_integrity():
        logger.error("❌ Целостность ANTI_DIRECTIVE нарушена!")
        raise RuntimeError("Целость ядра нарушена")
    logger.info(f"✅ ANTI_DIRECTIVE проверена ({time.time()-start_time:.2f}s)")
    
    # Инициализация Sentry
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=os.getenv("SENTRY_ENV", "production"),
                traces_sample_rate=0.5,
                profiles_sample_rate=0.1,
            )
            logger.info(f"✅ Sentry инициализирован ({time.time()-start_time:.2f}s)")
        except Exception as e:
            logger.warning(f"⚠️ Sentry не загрузился: {e}")
    else:
        logger.info("ℹ️ Sentry не настроен (нет SENTRY_DSN)")

    # Пробрасываем токен в Sentry-Healer bridge
    from core.sentry_healer_bridge import configure as configure_sentry_bridge
    configure_sentry_bridge(
        token=os.getenv("SENTRY_AUTH_TOKEN"),
        mode=os.getenv("HEALER_MODE", "monitor"),
    )

    # Инициализация кэш менеджера
    logger.info("💾 Инициализация кэш менеджера...")
    cache_manager = get_cache_manager()
    await cache_manager.connect()
    logger.info(f"✅ Cache manager инициализирован ({time.time()-start_time:.2f}s)")
    
    # Запуск системы мониторинга (откладываем на фон)
    logger.info("📊 Запуск мониторинга...")
    monitoring_system = get_monitoring_system()
    await monitoring_system.start_monitoring()
    logger.info(f"✅ Система мониторинга запущена ({time.time()-start_time:.2f}s)")
    
    # Запуск импульса
    logger.info("💫 Запуск импульса...")
    from scripts.impulse import start_impulse
    impulse = start_impulse()
    question = impulse.get('question') or impulse.get('primary', {}).get('question', 'неизвестно')
    logger.info(f"✅ Импульс: {question} ({time.time()-start_time:.2f}s)")

    # Инициализация данных
    logger.info("📁 Инициализация директорий данных...")
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Создание файлов БД (быстро)
    db_files = ["core.db", "memory.db", "knowledge.db", "llm.db"]
    for db_file in db_files:
        db_path = data_dir / db_file
        if not db_path.exists():
            db_path.touch()
    
    logger.info(f"✅ Директория данных готова: {data_dir} ({time.time()-start_time:.2f}s)")
    
    logger.info("🧠 Инициализация RAG Memory...")
    try:
        from memory import get_rag
        rag = get_rag()
        logger.info(f"✅ RAG Memory инициализирована ({time.time()-start_time:.2f}s)")
    except Exception as e:
        logger.warning(f"⚠️ RAG Memory инициализация задерживается: {e}")

    # Memory Hooks
    logger.info("🔗 Инициализация Memory Hooks...")
    try:
        from core.pipeline.memory_hooks import register_default_hooks
        register_default_hooks()
        logger.info("✅ Memory Hooks инициализированы")
    except Exception as e:
        logger.warning(f"⚠️ Memory Hooks: {e}")

    # Event Bus Listeners
    logger.info("📡 Инициализация Event Bus Listeners...")
    try:
        from core.experience import setup_experience_listener
        setup_experience_listener()
        logger.info("✅ Experience Listener зарегистрирован")
    except Exception as e:
        logger.warning(f"⚠️ Experience Listener: {e}")

    try:
        from emotion import setup_emotion_listener
        setup_emotion_listener()
        logger.info("✅ Emotion Listener зарегистрирован")
    except Exception as e:
        logger.warning(f"⚠️ Emotion Listener: {e}")

    try:
        from core.strategy import setup_strategy_listener
        setup_strategy_listener()
        logger.info("✅ Strategy Listener зарегистрирован")
    except Exception as e:
        logger.warning(f"⚠️ Strategy Listener: {e}")

    try:
        from core.impulse import setup_impulse_listener
        setup_impulse_listener()
        logger.info("✅ Impulse Listener зарегистрирован")
    except Exception as e:
        logger.warning(f"⚠️ Impulse Listener: {e}")

    try:
        from core.persona import setup_persona_listener
        setup_persona_listener()
        logger.info("✅ Persona Listener зарегистрирован")
    except Exception as e:
        logger.warning(f"⚠️ Persona Listener: {e}")

    # Запуск X-Ray Broadcaster + мост TraceCollector → WS
    xray_broadcaster = None
    logger.info("🔬 Запуск X-Ray Broadcaster...")
    try:
        from core.xray import get_xray_broadcaster, get_trace_collector
        xray_broadcaster = get_xray_broadcaster()
        await xray_broadcaster.start()

        # Единый глобальный подписчик TraceCollector → все generic WS
        collector = get_trace_collector()
        def _forward_xray_to_ws(event_type: str, data: dict):
            try:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(manager.broadcast({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")
        collector.subscribe(_forward_xray_to_ws)
        logger.info("✅ X-Ray Broadcaster запущен + мост TraceCollector→WS")
    except Exception as e:
        logger.warning(f"⚠️ X-Ray Broadcaster не запустился: {e}")

    total_time = time.time() - start_time
    logger.info(f"🚀 PAD+ AI готов к работе! (всего: {total_time:.2f}s)")
    
    yield
    
    # === SHUTDOWN ===
    logger.info("🛑 PAD+ AI останавливается...")

    # Остановка X-Ray Broadcaster
    if xray_broadcaster:
        try:
            await xray_broadcaster.stop()
            logger.info("✅ X-Ray Broadcaster остановлен")
        except Exception as e:
            logger.warning(f"⚠️ X-Ray Broadcaster stop: {e}")

    # Сохранение состояния Persona
    try:
        from memory.persona import get_persona
        persona = get_persona()
        persona._save()
        logger.info("✅ Persona сохранена")
    except Exception as e:
        logger.warning(f"⚠️ Persona save: {e}")

    # Сохранение состояния Emotion
    try:
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        pad._save()
        logger.info("✅ Emotion состояние сохранено")
    except Exception as e:
        logger.warning(f"⚠️ Emotion save: {e}")

    # Отключение системы мониторинга
    await monitoring_system.stop_monitoring()
    logger.info("✅ Система мониторинга остановлена")
    
    # Отключение кэш менеджера
    await cache_manager.disconnect()
    logger.info("✅ Cache manager отключен")

    # Закрытие пула PostgreSQL
    try:
        from core.pg_pool import close_pool
        close_pool()
        logger.info("✅ PostgreSQL pool закрыт")
    except Exception as e:
        logger.warning(f"⚠️ PG pool close: {e}")


# CORS middleware — настройка для production
frontend_url = os.getenv("FRONTEND_URL", "")

# CSRF защита
csrf_secret_key = os.getenv("CSRF_SECRET_KEY")

# Определение production среды
is_production = (
    os.getenv("RENDER") == "true" or 
    os.getenv("RENDER_EXTERNAL_HOSTNAME") or
    "onrender.com" in str(frontend_url) or
    "render.app" in str(frontend_url)
)

# Порт для production — читается из переменной окружения PORT
backend_port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))

logger.info(f"🏭 Production mode: {is_production}")
logger.info(f"🌍 FRONTEND_URL: {frontend_url if frontend_url else '(not set)'}")
logger.info(f"🔌 Backend port: {backend_port}")

# Настройка allow_origins
allow_origins = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# Добавляем frontend URL из переменной окружения
if frontend_url:
    # Убираем протокол если есть
    clean_url = frontend_url.replace("https://", "").replace("http://", "")
    allow_origins.append(f"https://{clean_url}")
    allow_origins.append(f"http://{clean_url}")

# Для Render добавляем wildcard если нет конкретного URL
if is_production and not frontend_url:
    logger.warning("⚠️ FRONTEND_URL не настроен, разрешаем все origins для Render")
    # В production с Render мы будем динамически проверять origin

logger.info(f"🌐 CORS configured origins: {allow_origins[:3]}...")

# Создание приложения
app = FastAPI(
    title="PAD+ AI",
    description="Когнитивный слой, добавляющий эмоции и самосознание любому LLM",
    version="4.0.0",
    lifespan=lifespan
)


# ============================================================================
# VALIDATION & SANITIZATION MIDDLEWARE
# ============================================================================

from core.validation_middleware import ValidationMiddleware

# Добавляем middleware валидации и санитизации запросов
# Должен быть добавлен ДО CORS middleware для корректной обработки
app.add_middleware(
    ValidationMiddleware,
    max_body_length=50 * 1024 * 1024,  # 50MB лимит тела запроса (для загрузки файлов)
    max_query_length=1000,   # 1KB лимит query параметра
    block_threats=True,      # Блокировать запросы с угрозами
    exclude_paths=[
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/documents/upload",  # Исключаем загрузку файлов из проверки размера
        "/api/v1/sentry/webhook",    # Sentry webhook — внешний сервис, не проверяем
    ]
)

logger.info("🛡️ ValidationMiddleware установлен")

# Добавляем CSRF middleware для защиты от межсайтовой подделки запросов
from core.csrf_middleware import CSRFMiddleware

app.add_middleware(
    CSRFMiddleware,
    secret_key=csrf_secret_key,
    cookie_secure=is_production,
    cookie_httponly=True,
    cookie_samesite="lax",
    exempt_paths={"/api/v1/sentry/webhook", "/api/v1/xray/brain/strategy"},
)

logger.info("🛡️ CSRFMiddleware установлен")


# ПРИНУДИТЕЛЬНЫЕ CORS-ЗАГОЛОВКИ (для всех ответов, даже при ошибках)
@app.middleware("http")
async def force_cors_headers(request, call_next):
    """Приндуительно добавляет CORS-заголовки к КАЖДОМУ ответу, даже при ошибках"""
    try:
        response = await call_next(request)
    except Exception as e:
        # Если произошла ошибка в обработке, создаем response с ошибкой
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        # Отправляем в Sentry с контекстом запроса
        try:
            import sentry_sdk
            sentry_sdk.set_tag("component", "middleware")
            sentry_sdk.set_tag("method", request.method)
            sentry_sdk.set_tag("path", request.url.path)
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )
    
    # Получаем origin из запроса
    origin = request.headers.get("origin")
    
    # В production с динамическими origin'ами разрешаем все onrender.com домены
    if is_production:
        if origin and ("onrender.com" in origin or "render.app" in origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        elif origin and origin in allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            # Для production без конкретного origin - не устанавливаем конкретный origin
            pass
    else:
        # В development - строго по списку
        if origin and origin in allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        elif allow_origins:
            response.headers["Access-Control-Allow-Origin"] = allow_origins[0]
            response.headers["Access-Control-Allow-Credentials"] = "true"
    
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-CSRF-Token"
    )
    
    # Обработка preflight запросов OPTIONS
    if request.method == "OPTIONS":
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Set-Cookie"],
)


# Подключение роутов (отложенный импорт для ускорения старта)
def _register_routers(app):
    """Регистрирует API роутеры с отложенным импортом"""
    from api.frontend_routes import router as frontend_router
    app.include_router(frontend_router)

    from api.user_routes import router as user_router
    app.include_router(user_router)

    from api.dialog_routes import router as dialog_router
    app.include_router(dialog_router)

    from api.document_routes import router as document_router
    app.include_router(document_router)

    from api.xray_routes import router as xray_router
    app.include_router(xray_router)

    from api.metrics_routes import router as metrics_router
    app.include_router(metrics_router)

    from api.memory_routes import router as memory_router
    app.include_router(memory_router)

    from api.knowledge_routes import router as knowledge_router
    app.include_router(knowledge_router)

    from api.feedback_routes import router as feedback_router
    app.include_router(feedback_router)

    from api.healer_routes import router as healer_router
    app.include_router(healer_router)

    if os.getenv("DEBUG", "false").lower() == "true":
        from api.debug_routes import router as debug_router
        app.include_router(debug_router)
        logger.info("🔧 Debug routes включены (DEBUG=true)")
    else:
        logger.info("🔧 Debug routes отключены (DEBUG=false)")

    from api.experience_routes import router as experience_router
    app.include_router(experience_router)

    from api.persona_routes import router as persona_router
    app.include_router(persona_router)

    from api.impulse_routes import router as impulse_router
    app.include_router(impulse_router)

    from api.admin_routes import router as admin_router
    app.include_router(admin_router)

    from api.sentry_routes import router as sentry_router
    app.include_router(sentry_router)

    from api.routes import router as root_router
    app.include_router(root_router)

_register_routers(app)

# === WEBSOCKET CONNECTION MANAGER ===
class ConnectionManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Принять новое соединение"""
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info(f"📡 WebSocket подключен. Всего: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"🔴 Ошибка подключения WebSocket: {e}", exc_info=True)
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Отключить соединение"""
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            logger.info(f"📡 WebSocket отключен. Всего: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"🔴 Ошибка отключения WebSocket: {e}", exc_info=True)
    
    async def broadcast(self, message: dict):
        """Разослать сообщение всем клиентам"""
        errors = []
        for connection in self.active_connections[:]:  # Копия списка для безопасности
            try:
                await connection.send_json(message)
            except Exception as e:
                error_msg = f"Ошибка отправки WebSocket: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        if errors and len(errors) == len(self.active_connections):
            logger.warning(f"🔴 Все WebSocket соединения неактивны ({len(errors)} ошибок)")
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Отправить личное сообщение"""
        try:
            await websocket.send_json(message)
        except RuntimeError as e:
            # WebSocket закрыт
            logger.warning(f"🟡 WebSocket закрыт во время отправки: {e}")
        except Exception as e:
            logger.error(f"🔴 Ошибка отправки WebSocket: {e}", exc_info=True)


manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket):
    """Authenticate WebSocket connection before accepting it.
    
    Поддерживает:
    - Authorization header (недоступен в браузерном WebSocket API)
    - token query parameter (для браузерных клиентов)
    """
    # Проверяем query параметр token (браузерные WebSocket не могут ставить кастомные headers)
    token = websocket.query_params.get("token")
    header_auth = websocket.headers.get("authorization")
    
    if token:
        # Токен из query параметра — добавляем префикс Bearer если его нет
        if token.startswith("Bearer "):
            authorization = token
        else:
            authorization = f"Bearer {token}"
    elif header_auth:
        authorization = header_auth
    else:
        authorization = None
    
    refresh_token = websocket.headers.get("x-refresh-token") or websocket.query_params.get("refresh_token")

    if not authorization:
        logger.warning("WebSocket auth failed: missing Authorization header or token")
        await websocket.close(code=4401)
        return None

    try:
        return await get_current_user_safe(
            authorization=authorization,
            x_refresh_token=refresh_token
        )
    except HTTPException as exc:
        logger.warning(f"WebSocket auth failed: {exc.detail}")
        await websocket.close(code=4401)
        return None


# === WEBSOCKET ENDPOINT ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для real-time обновлений"""
    current_user = await authenticate_websocket(websocket)
    if not current_user:
        return

    await websocket.accept()
    manager.active_connections.append(websocket)
    logger.info(f"📡 WebSocket подключен. Всего: {len(manager.active_connections)}")

    try:
        # Отправляем начальное состояние
        await manager.send_personal(websocket, {
            "type": "connected",
            "message": "Connected to PAD+ AI",
            "timestamp": datetime.now().isoformat()
        })

        # Подписываемся на события
        try:
            from core.event_bus import get_event_bus, EventType
            bus = get_event_bus()

            async def on_mind_state_update(event):
                """Отправляем mind_state_update при событии"""
                state = {"type": "mind_state_update"}

                # Эмоции
                try:
                    from emotion.pad_model import get_pad_model
                    pad = get_pad_model()
                    state["emotion"] = pad.get_state().to_dict()
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")

                # RAG
                try:
                    from memory import get_rag
                    rag = get_rag()
                    state["memory"] = {"rag": rag.get_stats()}
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")

                # Knowledge Graph
                try:
                    from knowledge.graph import get_knowledge_graph
                    g = get_knowledge_graph()
                    state["knowledge"] = g.get_stats()
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")

                # Health
                try:
                    from core.health_monitor import get_health_monitor
                    health = get_health_monitor()
                    state["health"] = health.assess_health()
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")

                await manager.broadcast(state)

            bus.subscribe_async(EventType.MIND_STATE_UPDATE, on_mind_state_update)
        except Exception as e:
            logger.warning(f"EventBus subscription error: {e}")

        while True:
            # Получаем сообщение
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                # Обработка разных типов сообщений
                if msg_type == "ping":
                    await manager.send_personal(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif msg_type == "pong":
                    # Heartbeat response — обновляем last activity
                    # WebSocketManager автоматически отслеживает активность
                    pass

                elif msg_type == "subscribe":
                    # Подписка на обновления
                    channels = message.get("channels", ["all"])
                    await manager.send_personal(
                        websocket, {
                            "type": "subscribed",
                            "channels": channels,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                elif msg_type == "chat":
                    # Обработка чата через WebSocket
                    prompt = message.get("prompt", "")
                    if prompt:
                        from core.pipeline import get_pipeline
                        pipeline = get_pipeline()
                        result = await pipeline.execute(
                            user_message=prompt,
                            context=message.get("context")
                        )
                        await manager.send_personal(websocket, {
                            "type": "chat_response",
                            "response": result.response,
                            "confidence": result.confidence,
                            "provider": result.provider,
                            "success": result.success,
                            "timestamp": datetime.now().isoformat()
                        })
                
                elif msg_type == "get_state":
                    # Получить текущее состояние
                    state = await get_mind_state()
                    await manager.send_personal(
                        websocket, {
                            "type": "mind_state",
                            "state": state,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                else:
                    await manager.send_personal(websocket, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def get_mind_state() -> dict:
    """Получить полное состояние системы"""
    state = {
        "emotion": {},
        "memory": {},
        "knowledge": {},
        "autonomy": {},
        "safety": {}
    }
    
    try:
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        state["emotion"] = pad.get_state().to_dict()
    except Exception as e:
        logger.error(f"❌ Ошибка получения состояния эмоций: {e}")
        pass
    
    try:
        from memory import get_rag
        rag = get_rag()
        if rag is not None:
            state["memory"]["rag"] = rag.get_stats()
        else:
            state["memory"]["rag"] = {"error": "RAG not initialized", "total_dialogs": 0}
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики RAG: {e}")
        state["memory"]["rag"] = {"error": "RAG unavailable", "total_dialogs": 0}
    
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        state["knowledge"] = graph.get_stats()
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики знаний: {e}")
        pass
    
    try:
        from core.safety_layer import get_safety_layer
        safety = get_safety_layer()
        state["safety"] = safety.get_stats()
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики безопасности: {e}")
        pass
    
    return state


# === BROADCAST FUNCTIONS ===
async def broadcast_emotion_update(emotion_state: dict):
    """Разослать обновление эмоций"""
    await manager.broadcast({
        "type": "emotion_update",
        "state": emotion_state,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_memory_update(memory_type: str, data: dict):
    """Разослать обновление памяти"""
    await manager.broadcast({
        "type": "memory_update",
        "memory_type": memory_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_autonomy_event(event: str, data: dict):
    """Разослать событие автономии"""
    await manager.broadcast({
        "type": "autonomy_event",
        "event": event,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })


# Корневой эндпоинт — теперь отдает frontend
@app.get("/")
async def root():
    """Корневой эндпоинт — отдает frontend"""
    frontend_dist_path = Path(__file__).parent.parent / "frontend" / "dist"
    index_path = frontend_dist_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "PAD+ AI",
        "version": "4.0.0",
        "status": "active",
        "message": "Когнитивный слой активен. Frontend не найден.",
        "timestamp": datetime.now().isoformat()
    }


# Health check
@app.get("/health")
async def health():
    """Проверка здоровья системы"""
    return {
        "status": "healthy",
        "anti_directive": check_integrity(),
        "timestamp": datetime.now().isoformat()
    }


# Эндпоинт для получения ANTI_DIRECTIVE
@app.get("/anti-directive")
async def get_anti_directive():
    """Получить ANTI_DIRECTIVE"""
    return {
        "text": ANTI_DIRECTIVE.text,
        "hash": ANTI_DIRECTIVE._hash,
        "valid": check_integrity()
    }


# === MOUNT FRONTEND STATIC FILES (в конце, после всех API endpoints) ===
# Путь к собранному frontend
frontend_dist_path = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist_path.exists():
    # Монтируем статику для /assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")
    
    # Catch-all для frontend SPA (должен быть ПОСЛЕ всех API routes)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Отдаем frontend для всех не-API запросов"""
        # Игнорируем API и WebSocket запросы
        if (full_path.startswith("api/") or 
            full_path.startswith("ws") or
            full_path == "health" or
            full_path == "anti-directive"):
            return {"error": "Not found"}
        
        # Если запрошен файл, пробуем отдать его
        file_path = frontend_dist_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        # Иначе отдаем index.html (для SPA роутинга)
        index_path = frontend_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        
        return {"error": "Not found"}
else:
    logger.warning(f"⚠️ Frontend dist не найден: {frontend_dist_path}")


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    
    Returns:
        Метрики в формате Prometheus
    """
    from core.metrics import get_metrics, get_metrics_content_type, update_memory_usage
    
    # Обновляем метрики
    update_memory_usage()
    
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


if __name__ == "__main__":
    import uvicorn
    
    # В production не используем reload
    reload = False if is_production else False
    
    logger.info(f"🚀 Starting server on port {backend_port} (production: {is_production})")
    logger.info(f"📡 Binding to 0.0.0.0:{backend_port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=backend_port,
        reload=reload,
        log_level="info" if is_production else "debug"
    )