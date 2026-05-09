"""
Упрощенный backend для тестирования - без зависимостей которые могут блокировать запуск
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("padplus.simple")

# Создание FastAPI приложения
app = FastAPI(
    title="PAD+ AI Simple API",
    version="1.0.0",
    description="Упрощенный API для тестирования"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Простые эндпоинты для тестирования
@app.get("/")
async def root():
    return {"message": "PAD+ AI Simple API работает"}

@app.get("/api/v1/providers")
async def get_providers():
    """Простой список провайдеров для тестирования"""
    return [
        {"id": "gigachat", "name": "GigaChat", "description": "Модели GigaChat от Сбера", "free_models": ["gigachat/GigaChat-2-Lite"]},
        {"id": "openai", "name": "OpenAI", "description": "Модели OpenAI", "free_models": []},
        {"id": "google", "name": "Google", "description": "Модели Google Gemini", "free_models": []}
    ]

@app.get("/api/v1/health")
async def health_check():
    """Проверка здоровья"""
    return {"status": "healthy", "backend": "simple"}

@app.get("/api/v1/keys")
async def get_keys():
    """Заглушка для ключей - требует авторизации"""
    return {"detail": {"error": "authorization_required", "message": "Требуется авторизация"}}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Запуск упрощенного backend на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
