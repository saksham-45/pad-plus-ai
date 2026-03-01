#!/usr/bin/env python3
"""
Тестирование работоспособности системы перед деплоем

Этот скрипт проверяет:
1. CORS middleware конфигурацию
2. RAG память и зависимости
3. GigaChat подключение
4. Переменные окружения
5. Базовые API эндпоинты
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("health_check")

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def check_environment_variables():
    """Проверка переменных окружения"""
    logger.info("🔍 Проверка переменных окружения...")
    
    required_vars = [
        "FRONTEND_URL",
        "OPENROUTER_API_KEY"
    ]
    
    optional_vars = [
        "GIGACHAT_AUTHORIZATION_KEY",
        "RENDER_EXTERNAL_HOSTNAME"
    ]
    
    results = {
        "required": {},
        "optional": {},
        "production_mode": False
    }
    
    # Проверяем required переменные
    for var in required_vars:
        value = os.getenv(var)
        results["required"][var] = {
            "present": value is not None,
            "value": value if value else "not set"
        }
        if value:
            logger.info(f"✅ {var}: {value}")
        else:
            logger.error(f"❌ {var}: not set")
    
    # Проверяем optional переменные
    for var in optional_vars:
        value = os.getenv(var)
        results["optional"][var] = {
            "present": value is not None,
            "value": value if value else "not set"
        }
        if value:
            logger.info(f"✅ {var}: {value}")
        else:
            logger.warning(f"⚠️ {var}: not set (optional)")
    
    # Определяем production mode
    is_production = (
        os.getenv("RENDER") or 
        os.getenv("RENDER_EXTERNAL_HOSTNAME") or
        "onrender.com" in str(os.getenv("FRONTEND_URL", ""))
    )
    results["production_mode"] = bool(is_production)
    
    logger.info(f"🏭 Production mode: {is_production}")
    
    return results

def check_cors_configuration():
    """Проверка CORS middleware конфигурации"""
    logger.info("🌐 Проверка CORS middleware...")
    
    try:
        from main import frontend_url, is_production, allow_origins
        
        results = {
            "frontend_url": frontend_url,
            "is_production": is_production,
            "allow_origins": allow_origins,
            "has_frontend_url": frontend_url != "http://localhost:5173",
            "has_production_origins": any("onrender.com" in origin for origin in allow_origins)
        }
        
        logger.info(f"✅ Frontend URL: {frontend_url}")
        logger.info(f"✅ Production mode: {is_production}")
        logger.info(f"✅ Allow origins: {allow_origins}")
        
        if results["has_frontend_url"]:
            logger.info("✅ Frontend URL настроен")
        else:
            logger.warning("⚠️ Frontend URL не настроен (используется localhost)")
        
        if results["has_production_origins"]:
            logger.info("✅ Production origins настроены")
        else:
            logger.warning("⚠️ Production origins не настроены")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки CORS: {e}")
        return {"error": str(e)}

async def check_rag_memory():
    """Проверка RAG памяти"""
    logger.info("🧠 Проверка RAG памяти...")
    
    try:
        from memory.rag import get_rag
        
        rag = get_rag()
        stats = rag.get_stats()
        
        results = {
            "total_dialogs": stats.get("total_dialogs", 0),
            "version": stats.get("version", "unknown"),
            "persist_dir": stats.get("persist_dir", "unknown"),
            "features": stats.get("features", {}),
            "topic_distribution": stats.get("topic_distribution", {}),
            "sentiment_distribution": stats.get("sentiment_distribution", {}),
            "total_entities": stats.get("total_entities", 0),
            "total_relations": stats.get("total_relations", 0)
        }
        
        logger.info(f"✅ RAG инициализирована: {results['total_dialogs']} диалогов")
        logger.info(f"✅ Версия: {results['version']}")
        logger.info(f"✅ Директория: {results['persist_dir']}")
        logger.info(f"✅ Темы: {len(results['topic_distribution'])}")
        logger.info(f"✅ Сущности: {results['total_entities']}")
        logger.info(f"✅ Связи: {results['total_relations']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка RAG памяти: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

async def check_gigachat():
    """Проверка GigaChat подключения"""
    logger.info("🤖 Проверка GigaChat...")
    
    try:
        from llm.gigachat import gigachat
        
        health = await gigachat.check_health()
        
        results = {
            "enabled": gigachat.enabled,
            "status": health["status"],
            "message": health["message"],
            "has_token": gigachat.token is not None
        }
        
        if gigachat.enabled:
            logger.info(f"✅ GigaChat включен: {health['status']}")
            logger.info(f"✅ Сообщение: {health['message']}")
        else:
            logger.warning("⚠️ GigaChat отключен (ключ не настроен)")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка GigaChat: {e}")
        return {"error": str(e)}

async def check_api_endpoints():
    """Проверка API эндпоинтов"""
    logger.info("🔌 Проверка API эндпоинтов...")
    
    try:
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        results = {}
        
        # Проверяем основные эндпоинты
        endpoints = [
            "/",
            "/health",
            "/anti-directive",
            "/api/v1/rag/stats",
            "/api/v1/emotion/state",
            "/api/v1/mind-state"
        ]
        
        for endpoint in endpoints:
            try:
                response = client.get(endpoint)
                results[endpoint] = {
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "has_data": len(response.text) > 10
                }
                
                if response.status_code < 400:
                    logger.info(f"✅ {endpoint}: {response.status_code}")
                else:
                    logger.warning(f"⚠️ {endpoint}: {response.status_code}")
                    
            except Exception as e:
                results[endpoint] = {
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                }
                logger.error(f"❌ {endpoint}: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки API: {e}")
        return {"error": str(e)}

async def check_dependencies():
    """Проверка зависимостей"""
    logger.info("📦 Проверка зависимостей...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "chromadb",
        "httpx",
        "pydantic"
    ]
    
    optional_packages = [
        "openai",
        "anthropic",
        "google-generativeai"
    ]
    
    results = {
        "required": {},
        "optional": {}
    }
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            results["required"][package] = True
            logger.info(f"✅ {package}")
        except ImportError:
            results["required"][package] = False
            logger.error(f"❌ {package} не установлен")
    
    for package in optional_packages:
        try:
            __import__(package.replace("-", "_"))
            results["optional"][package] = True
            logger.info(f"✅ {package}")
        except ImportError:
            results["optional"][package] = False
            logger.warning(f"⚠️ {package} не установлен")
    
    return results

async def run_health_check():
    """Запуск полной проверки системы"""
    logger.info("🚀 Запуск проверки системы...")
    
    start_time = datetime.now()
    
    # Собираем результаты
    results = {
        "timestamp": start_time.isoformat(),
        "environment": check_environment_variables(),
        "cors": check_cors_configuration(),
        "dependencies": await check_dependencies(),
        "rag": await check_rag_memory(),
        "gigachat": await check_gigachat(),
        "api": await check_api_endpoints()
    }
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    results["duration_seconds"] = duration
    
    # Анализ общего состояния
    issues = []
    warnings = []
    
    # Проверяем environment
    if not results["environment"]["required"]["FRONTEND_URL"]["present"]:
        issues.append("FRONTEND_URL не настроен")
    
    if not results["environment"]["required"]["OPENROUTER_API_KEY"]["present"]:
        issues.append("OPENROUTER_API_KEY не настроен")
    
    # Проверяем CORS
    if "error" in results["cors"]:
        issues.append("CORS middleware не работает")
    elif not results["cors"]["has_production_origins"]:
        warnings.append("Production origins не настроены")
    
    # Проверяем RAG
    if "error" in results["rag"]:
        issues.append("RAG память не работает")
    
    # Проверяем зависимости
    missing_required = [pkg for pkg, present in results["dependencies"]["required"].items() if not present]
    if missing_required:
        issues.append(f"Отсутствуют зависимости: {missing_required}")
    
    # Проверяем API
    failed_endpoints = [ep for ep, data in results["api"].items() 
                       if isinstance(data, dict) and not data.get("success", False)]
    if failed_endpoints:
        issues.append(f"API эндпоинты не работают: {failed_endpoints}")
    
    results["issues"] = issues
    results["warnings"] = warnings
    results["status"] = "healthy" if not issues else "unhealthy"
    
    # Выводим результаты
    logger.info("=" * 50)
    logger.info("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    logger.info("=" * 50)
    
    if issues:
        logger.error("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
        for issue in issues:
            logger.error(f"  - {issue}")
    
    if warnings:
        logger.warning("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    if not issues and not warnings:
        logger.info("✅ Система готова к деплою!")
    
    logger.info(f"⏱️ Время проверки: {duration:.2f} секунд")
    
    # Сохраняем отчет
    report_file = Path(__file__).parent / "health_check_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📄 Отчет сохранен: {report_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_health_check())