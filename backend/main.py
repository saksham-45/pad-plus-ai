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

# Загружаем переменные окружения из .env файла
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Настройка логирования
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
from api import routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # === STARTUP ===
    logger.info("🧠 PAD+ AI v3.5 запускается...")
    
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


# CORS middleware — настройка для production
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allow_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173", 
    "http://localhost:3000",
    frontend_url
]

# Автоматическое определение production среды
is_production = (
    os.getenv("RENDER") or 
    os.getenv("RENDER_EXTERNAL_HOSTNAME") or
    "onrender.com" in str(frontend_url)
)

if is_production:
    # Добавляем production URL из переменной окружения
    if frontend_url and "onrender.com" in frontend_url:
        allow_origins.append(frontend_url)
    else:
        # Резервные варианты для Render
        allow_origins.extend([
            "https://padplus-ai-frontend.onrender.com",
            "https://padplus-ai-backend.onrender.com"
        ])
else:
    # Для локальной разработки добавляем дополнительные origins
    allow_origins.extend([
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173"
    ])

# Убедимся, что все origins уникальны
allow_origins = list(set(allow_origins))

logger.info(f"🌐 CORS настроен для origins: {allow_origins}")
logger.info(f"🏭 Production mode: {is_production}")

# Создание приложения
app = FastAPI(
    title="PAD+ AI",
    description="Когнитивный слой, добавляющий эмоции и самосознание любому LLM",
    version="3.5.0",
    lifespan=lifespan
)


# ПРИНУДИТЕЛЬНЫЕ CORS-ЗАГОЛОВКИ (для всех ответов, даже при ошибках)
@app.middleware("http")
async def force_cors_headers(request, call_next):
    """Принудительно добавляет CORS-заголовки к КАЖДОМУ ответу, даже при ошибках"""
    try:
        response = await call_next(request)
    except Exception as e:
        # Если произошла ошибка в обработке, создаем response с ошибкой
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )
    
    # ПРИНУДИТЕЛЬНО добавляем CORS-заголовки к любому ответу
    origin = request.headers.get("origin")
    if origin and origin in allow_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        # Если origin не в списке, используем первый разрешенный
        response.headers["Access-Control-Allow-Origin"] = (
            allow_origins[0] if allow_origins else "*"
        )
    
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization"
    )
    
    # Обработка preflight запросов OPTIONS
    if request.method == "OPTIONS":
        return response
    
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключение роутов
app.include_router(routes.router, prefix="/api/v1")


# === WEBSOCKET CONNECTION MANAGER ===
class ConnectionManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Принять новое соединение"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"📡 WebSocket подключен. Всего: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Отключить соединение"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"📡 WebSocket отключен. Всего: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Разослать сообщение всем клиентам"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Ошибка отправки: {e}")
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Отправить личное сообщение"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")


manager = ConnectionManager()


# === WEBSOCKET ENDPOINT ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для real-time обновлений"""
    await manager.connect(websocket)
    
    try:
        # Отправляем начальное состояние
        await manager.send_personal(websocket, {
            "type": "connected",
            "message": "Connected to PAD+ AI",
            "timestamp": datetime.now().isoformat()
        })
        
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


# Корневой эндпоинт
@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": "PAD+ AI",
        "version": "3.5.0",
        "status": "active",
        "message": "Когнитивный слой активен",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )