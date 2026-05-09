#!/usr/bin/env python3
"""
Production server starter for Render
Продакшн скрипт запуска для Render с поддержкой gunicorn
"""

import os
import sys
import logging
import time
import subprocess

# Добавляем backend в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("server_starter")

logger.info("🚀 Starting PAD+ AI server...")
logger.info(f"📁 Working directory: {os.getcwd()}")
logger.info(f"📂 Python path: {sys.path[:3]}")

# Проверяем PORT
port = os.getenv("PORT", "8000")
logger.info(f"🔌 Port: {port}")

# Определяем production среду
is_production = (
    os.getenv("RENDER") == "true" or 
    os.getenv("RENDER_EXTERNAL_HOSTNAME") or
    os.getenv("RENDER") is not None or  # Любое значение RENDER переменной
    "onrender.com" in os.getenv("RENDER_EXTERNAL_URL", "") or
    "render.app" in os.getenv("RENDER_EXTERNAL_URL", "")
)

logger.info(f"🏭 Production mode: {is_production}")
logger.info(f"🔎 RENDER env vars: RENDER={os.getenv('RENDER')}, RENDER_EXTERNAL_HOSTNAME={os.getenv('RENDER_EXTERNAL_HOSTNAME')}")

# Проверяем наличие файлов
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
main_py = os.path.join(backend_dir, 'main.py')

logger.info(f"📄 backend/main.py exists: {os.path.exists(main_py)}")
logger.info(f"📁 backend/ exists: {os.path.exists(backend_dir)}")

# Проверяем что модуль main можно импортировать
try:
    logger.info("📦 Attempting to import main.app...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", main_py)
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    logger.info("✅ Successfully imported main module")
except Exception as e:
    logger.error(f"❌ Failed to import main: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if is_production:
    # В production используем gunicorn
    logger.info("⚡ Starting gunicorn for production...")
    logger.info(f"📌 Running gunicorn on 0.0.0.0:{port}")
    
    cmd = [
        "gunicorn",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--workers", "1",
        "--bind", f"0.0.0.0:{port}",
        "--timeout", "120",
        "--keep-alive", "2",
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        "backend.main:app"
    ]
    
    logger.info(f"🔧 Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Gunicorn failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        sys.exit(0)
        
else:
    # В development используем uvicorn
    logger.info("⚡ Starting uvicorn for development...")
    logger.info(f"📌 Running uvicorn on 0.0.0.0:{port}")
    logger.info(f"🔍 Using backend.main:app with port={port} and host=0.0.0.0")

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(port),
        workers=1,
        log_level="info",
        reload=False  # Отключаем reload даже в dev для стабильности
    )

logger.info("✅ Server started successfully!")
