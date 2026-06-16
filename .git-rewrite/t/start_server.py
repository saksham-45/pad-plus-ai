#!/usr/bin/env python3
"""
Simple server starter for Render
Простой скрипт запуска для Render
"""

import os
import sys
import logging

# Добавляем backend в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("server_starter")

logger.info("🚀 Starting PAD+ AI server...")
logger.info(f"📁 Working directory: {os.getcwd()}")
logger.info(f"📂 Python path: {sys.path[:3]}")

# Проверяем PORT
port = os.getenv("PORT", "8000")
logger.info(f"🔌 Port: {port}")

# Проверяем наличие файлов
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
main_py = os.path.join(backend_dir, 'main.py')

logger.info(f"📄 backend/main.py exists: {os.path.exists(main_py)}")
logger.info(f"📁 backend/ exists: {os.path.exists(backend_dir)}")

# Запускаем uvicorn
import uvicorn

logger.info("⚡ Starting uvicorn...")

uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=int(port),
    workers=1,
    log_level="info"
)
