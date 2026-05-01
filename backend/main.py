"""
PAD+ AI v3.5 — Главный модуль

Когнитивный слой, добавляющий эмоции и самосознание любому LLM.
PAD+ = Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (в корне проекта) ДО всех импортов
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Настройка логирования (единожды)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("padplus")

# Импорт ядра
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.anti_directive import ANTI_DIRECTIVE, check_integrity
from core.cache_manager import get_cache_manager
from core.monitoring import get_monitoring_system
from core.dependencies import register_dependencies
from api import routes

# Импортируем core модули ПОСЛЕ загрузки .env
from core.supabase_client import get_supabase, check_database_connection

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # === STARTUP ===
    logger.info("🧠 PAD+ AI v3.5 запускается...")
    
    # Регистрация зависимостей (Вторая очередь улучшений)
    register_dependencies()
    logger.info("✅ Dependency Injection инициализирован")

    # Проверка целостности ANTI_DIRECTIVE
    if not check_integrity():
        logger.error("❌ Целостность ANTI_DIRECTIVE нарушена!")
        raise RuntimeError("Целостность ядра нарушена")
    logger.info("✅ ANTI_DIRECTIVE проверена")
    
    # Инициализация кэш менеджера
    cache_manager = get_cache_manager()
    await cache_manager.connect()
    logger.info("✅ Cache manager инициализирован")
    
    # Запуск системы мониторинга
    monitoring_system = get_monitoring_system()
    await monitoring_system.start_monitoring()
    logger.info("✅ Система мониторинга запущена")
    
    # Запуск импульса
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.impulse import start_impulse
    impulse = start_impulse()
    logger.info(f"✅ Импульс: {impulse['question']}")
    
    # Инициализация данных
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Директория данных: {data_dir}")
    
    # Создание файлов БД
    db_files = ["core.db", "memory.db", "knowledge.db", "llm.db"]
    for db_file in db_files:
        db_path = data_dir / db_file
        if not db_path.exists():
            db_path.touch()
            logger.info(f"✅ Создана БД: {db_file}")
    
    logger.info("🚀 PAD+ AI готов к работе!")
    
    yield
    
    # === SHUTDOWN ===
    logger.info("🛑 PAD+ AI останавливается...")

    # Отключение системы мониторинга
    await monitoring_system.stop_monitoring()
    logger.info("✅ Система мониторинга остановлена")
    
    # Отключение кэш менеджера
    await cache_manager.disconnect()
    logger.info("✅ Cache manager отключен")


# Создание приложения
app = FastAPI(
    title="PAD+ AI",
    description="Когнитивный слой, добавляющий эмоции и самосознание любому LLM",
    version="4.0.0",
    lifespan=lifespan
)


# ============================================================================
# 🔹 CORS MIDDLEWARE — ДОБАВЛЕН СРАЗУ ПОСЛЕ СОЗДАНИЯ app
# ============================================================================

# Разрешённые источники (CORS) — для локальной разработки и Render
allow_origins = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Render домены
    "https://pad-ai-v3-5.onrender.com",
    "https://pad-ai-backend.onrender.com",
    "https://padplus-ai-frontend.onrender.com",
    "https://padplus-ai-backend.onrender.com",
    # wildcard для *.onrender.com (для тестов)
    "https://*.onrender.com",
]

# Добавляем FRONTEND_URL из .env, если задан
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allow_origins:
    allow_origins.append(frontend_url)

# Убираем дубликаты
allow_origins = list(set(allow_origins))

logger.info(f"🌐 CORS настроен для {len(allow_origins)} origins")

# 🔹 Добавляем CORS middleware СРАЗУ после создания app (до других middleware!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# VALIDATION & SANITIZATION MIDDLEWARE
# ============================================================================

from core.validation_middleware import ValidationMiddleware

# Добавляем middleware валидации и санитизации запросов
app.add_middleware(
    ValidationMiddleware,
    max_body_length=50 * 1024 * 1024,  # 50MB лимит тела запроса
    max_query_length=1000,
    block_threats=True,
    exclude_paths=[
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/documents/upload",
    ]
)

logger.info("🛡️ ValidationMiddleware установлен")

# Добавляем CSRF middleware
from core.csrf_middleware import CSRFMiddleware
csrf_secret_key = os.getenv("CSRF_SECRET_KEY")

app.add_middleware(
    CSRFMiddleware,
    secret_key=csrf_secret_key,
    cookie_secure=False,
    cookie_httponly=True,
    cookie_samesite="lax",
)

logger.info("🛡️ CSRFMiddleware установлен")


# Подключение роутов
from api.frontend_routes import router as frontend_router
app.include_router(frontend_router)

from api.user_routes import router as user_router
app.include_router(user_router)

from api.dialog_routes import router as dialog_router
app.include_router(dialog_router)

from api.document_routes import router as document_router
app.include_router(document_router)

from api.file_routes import router as file_router
app.include_router(file_router)

from api.xray_routes import router as xray_router
app.include_router(xray_router)

from api.metrics_routes import router as metrics_router
app.include_router(metrics_router)


# === WEBSOCKET CONNECTION MANAGER ===
class ConnectionManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info(f"📡 WebSocket подключен. Всего: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"🔴 Ошибка подключения WebSocket: {e}", exc_info=True)
            raise
    
    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            logger.info(f"📡 WebSocket отключен. Всего: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"🔴 Ошибка отключения WebSocket: {e}", exc_info=True)
    
    async def broadcast(self, message: dict):
        errors = []
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception as e:
                error_msg = f"Ошибка отправки WebSocket: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        if errors and len(errors) == len(self.active_connections):
            logger.warning(f"🔴 Все WebSocket соединения неактивны ({len(errors)} ошибок)")
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except RuntimeError as e:
            logger.warning(f"🟡 WebSocket закрыт во время отправки: {e}")
        except Exception as e:
            logger.error(f"🔴 Ошибка отправки WebSocket: {e}", exc_info=True)


manager = ConnectionManager()


# === WEBSOCKET ENDPOINT ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для real-time обновлений"""
    await websocket.accept()
    manager.active_connections.append(websocket)
    logger.info(f"📡 WebSocket подключен. Всего: {len(manager.active_connections)}")

    try:
        await manager.send_personal(websocket, {
            "type": "connected",
            "message": "Connected to PAD+ AI",
            "timestamp": datetime.now().isoformat()
        })

        try:
            from core.event_bus import get_event_bus, EventType
            bus = get_event_bus()

            async def on_mind_state_update(event):
                state = {"type": "mind_state_update"}
                try:
                    from emotion.pad_model import get_pad_model
                    pad = get_pad_model()
                    state["emotion"] = pad.get_state().to_dict()
                except:
                    pass
                try:
                    from memory.rag import get_rag
                    rag = get_rag()
                    state["memory"] = {"rag": rag.get_stats()}
                except:
                    pass
                try:
                    from knowledge.graph import get_knowledge_graph
                    g = get_knowledge_graph()
                    state["knowledge"] = g.get_stats()
                except:
                    pass
                try:
                    from core.health_monitor import get_health_monitor
                    health = get_health_monitor()
                    state["health"] = health.assess_health()
                except:
                    pass
                await manager.broadcast(state)

            bus.subscribe_async(EventType.MIND_STATE_UPDATE, on_mind_state_update)
        except Exception as e:
            logger.warning(f"EventBus subscription error: {e}")

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                if msg_type == "ping":
                    await manager.send_personal(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif msg_type == "pong":
                    pass
                elif msg_type == "subscribe":
                    channels = message.get("channels", ["all"])
                    await manager.send_personal(websocket, {
                        "type": "subscribed",
                        "channels": channels,
                        "timestamp": datetime.now().isoformat()
                    })
                elif msg_type == "chat":
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
                    state = await get_mind_state()
                    await manager.send_personal(websocket, {
                        "type": "mind_state",
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    })
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
    except Exception:
        pass
    try:
        from memory.rag import get_rag
        rag = get_rag()
        state["memory"]["rag"] = rag.get_stats()
    except Exception:
        pass
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        state["knowledge"] = graph.get_stats()
    except Exception:
        pass
    try:
        from core.safety_layer import get_safety_layer
        safety = get_safety_layer()
        state["safety"] = safety.get_stats()
    except Exception:
        pass
    
    return state


# Корневой эндпоинт
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


# === MOUNT FRONTEND STATIC FILES ===
frontend_dist_path = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Отдаем frontend для всех не-API запросов"""
        if (full_path.startswith("api/") or 
            full_path.startswith("ws") or
            full_path == "health" or
            full_path == "anti-directive"):
            return {"error": "Not found"}
        
        file_path = frontend_dist_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        index_path = frontend_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        
        return {"error": "Not found"}
else:
    logger.warning(f"⚠️ Frontend dist не найден: {frontend_dist_path}")


# Prometheus metrics
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from core.metrics import get_metrics, get_metrics_content_type, update_memory_usage
    update_memory_usage()
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


if __name__ == "__main__":
    import uvicorn
    backend_port = int(os.getenv("BACKEND_PORT", "8080"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=backend_port,
        reload=False,  # ❗ Выключено для production (Render)
        log_level="info"
    )