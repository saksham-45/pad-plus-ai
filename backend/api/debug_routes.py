"""
🔧 Debug Routes — Диагностические эндпоинты для отладки провайдеров

Содержит:
- GET /api/v1/debug/gigachat — диагностика GigaChat
- GET /api/v1/debug/key-access — диагностика доступа к ключам
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger("padplus.debug")

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])


@router.get("/gigachat")
async def debug_gigachat():
    """
    Диагностика GigaChat — проверяет весь flow по шагам.
    
    Шаг 1: Проверка переменных окружения
    Шаг 2: Проверка URL
    Шаг 3: Проверка SSL
    Шаг 4: Проверка сетевой доступности (DNS + TCP)
    """
    import httpx
    import sys

    result = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "steps": [],
        "overall": "unknown",
        "recommendations": []
    }

    # === ШАГ 1: Переменные окружения ===
    env_check = {
        "name": "Переменные окружения",
        "status": "ok",
        "details": {}
    }

    env_vars = {
        "GIGACHAT_AUTH_KEY": os.getenv("GIGACHAT_AUTH_KEY"),
        "GIGACHAT_VERIFY_TLS": os.getenv("GIGACHAT_VERIFY_TLS", "false"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "ENCRYPTION_KEY": "SET" if os.getenv("ENCRYPTION_KEY") else "NOT SET",
        "SUPABASE_KEY": "SET" if os.getenv("SUPABASE_KEY") else "NOT SET",
        "SUPABASE_SERVICE_KEY": "SET" if os.getenv("SUPABASE_SERVICE_KEY") else "NOT SET",
    }

    for var_name, var_value in env_vars.items():
        if var_value and var_value != "NOT SET":
            if var_name == "GIGACHAT_AUTH_KEY":
                env_check["details"][var_name] = f"SET (len={len(var_value)})"
            elif var_name in ("SUPABASE_KEY", "SUPABASE_SERVICE_KEY"):
                if var_value and len(var_value) > 10:
                    env_check["details"][var_name] = f"SET (len={len(var_value)})"
                else:
                    env_check["details"][var_name] = "SET (looks too short)"
                    env_check["status"] = "warning"
            else:
                env_check["details"][var_name] = str(var_value)
        else:
            if var_name == "GIGACHAT_AUTH_KEY":
                env_check["details"][var_name] = "NOT SET (use system key for GigaChat)"
                env_check["status"] = "warning"  # Warning, not error — can use user key
            elif var_name.startswith("SUPABASE"):
                env_check["details"][var_name] = "NOT SET"
                env_check["status"] = "error"
            else:
                env_check["details"][var_name] = "NOT SET"

    result["steps"].append(env_check)

    # === ШАГ 2: Проверка URL ===
    from adapters.gigachat_client import GIGACHAT_AUTH_URL, GIGACHAT_API_URL

    url_check = {
        "name": "URL конфигурация",
        "status": "ok",
        "details": {
            "auth_url": GIGACHAT_AUTH_URL,
            "api_url": GIGACHAT_API_URL,
        }
    }

    import re
    for url_name, url in [("auth_url", GIGACHAT_AUTH_URL), ("api_url", GIGACHAT_API_URL)]:
        if not url.startswith("https://"):
            url_check["details"][f"{url_name}_problem"] = "URL не HTTPS!"
            url_check["status"] = "warning"
        if not re.match(r'^https://[\w\.\-]+(:\d+)?', url):
            url_check["details"][f"{url_name}_problem"] = "Некорректный формат URL"
            url_check["status"] = "warning"

    result["steps"].append(url_check)

    # === ШАГ 3: Проверка DNS резолва ===
    dns_check = {
        "name": "DNS резолв",
        "status": "ok",
        "details": {}
    }

    import socket
    for host_name in ["ngw.devices.sberbank.ru", "gigachat.devices.sberbank.ru"]:
        try:
            ip = socket.getaddrinfo(host_name, 443)
            dns_check["details"][host_name] = f"Resolved to {ip[0][4][0]}"
        except socket.gaierror as e:
            dns_check["details"][host_name] = f"DNS ERROR: {e}"
            dns_check["status"] = "error"

    result["steps"].append(dns_check)

    # === ШАГ 4: Проверка TCP доступности ===
    tcp_check = {
        "name": "TCP соединение (port check)",
        "status": "ok",
        "details": {}
    }

    for host_port in [
        ("ngw.devices.sberbank.ru", 9443),
        ("gigachat.devices.sberbank.ru", 443),
    ]:
        host, port = host_port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            result_code = s.connect_ex((host, port))
            s.close()
            if result_code == 0:
                tcp_check["details"][f"{host}:{port}"] = "OPEN"
            else:
                tcp_check["details"][f"{host}:{port}"] = f"CLOSED (error {result_code})"
                tcp_check["status"] = "error"
        except Exception as e:
            tcp_check["details"][f"{host}:{port}"] = f"ERROR: {e}"
            tcp_check["status"] = "error"

    result["steps"].append(tcp_check)

    # === ИТОГ ===
    errors = [s for s in result["steps"] if s["status"] == "error"]
    warnings = [s for s in result["steps"] if s["status"] == "warning"]

    if errors:
        result["overall"] = "error"
        result["recommendations"].append("❌ Есть критические ошибки. Исправьте их перед использованием GigaChat.")
    elif warnings:
        result["overall"] = "warning"
    else:
        result["overall"] = "ok"
        result["recommendations"].append("✅ Базовая сетевая доступность GigaChat в порядке.")

    if env_check["details"].get("GIGACHAT_AUTH_KEY", "").startswith("NOT"):
        result["recommendations"].append(
            "💡 GIGACHAT_AUTH_KEY не установлен — пользователи должны добавлять свои ключи GigaChat через UI."
            " Если вы хотите системный ключ, добавьте GIGACHAT_AUTH_KEY в .env"
        )

    return result


@router.get("/key-access")
async def debug_key_access(
    authorization: str = __import__("fastapi", fromlist=["Header"]).Header(None)
):
    """
    Диагностика доступа к API ключам.

    Требует: Authorization: Bearer <token>
    
    Проверяет:
    1. Есть ли пользователь в БД
    2. Есть ли ключи в таблице user_api_keys
    3. Работает ли расшифровка
    """
    from core.supabase_client import get_supabase, get_supabase_service
    from core.encryption import get_encryptor
    from core.auth_manager import get_current_user_safe

    if not authorization:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Требуется Authorization header (Bearer token)")

    current_user = await get_current_user_safe(authorization)
    if not current_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Недействительный токен")

    user_id = current_user["id"]
    result = {
        "user_id": user_id,
        "steps": [],
        "overall": "unknown"
    }

    # Шаг 1: Проверка наличия пользователя
    try:
        sb = get_supabase_service()
        if sb:
            user_check = sb.table("users").select("*").eq("id", user_id).execute()
            result["steps"].append({
                "name": "Пользователь в public.users",
                "status": "ok" if user_check.data else "error",
                "details": {
                    "found": bool(user_check.data),
                    "count": len(user_check.data) if user_check.data else 0
                }
            })
        else:
            result["steps"].append({
                "name": "Пользователь в public.users",
                "status": "warning",
                "details": {"error": "Service client not available"}
            })
    except Exception as e:
        result["steps"].append({
            "name": "Пользователь в public.users",
            "status": "error",
            "details": {"error": str(e)}
        })

    # Шаг 2: Проверка ключей
    try:
        db = get_supabase_service()
        if db:
            keys_result = db.table("user_api_keys")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            keys_data = keys_result.data if hasattr(keys_result, 'data') else []
            result["steps"].append({
                "name": "API ключи (user_api_keys)",
                "status": "ok" if keys_data else "warning",
                "details": {
                    "count": len(keys_data),
                    "providers": [k.get("provider") for k in keys_data],
                    "has_encrypted_keys": all(k.get("api_key_encrypted") for k in keys_data)
                }
            })

            # Шаг 3: Проверка расшифровки
            if keys_data:
                encryptor = get_encryptor()
                decrypt_errors = []
                for k in keys_data:
                    try:
                        decrypted = encryptor.decrypt(k["api_key_encrypted"])
                        if decrypted:
                            result["steps"].append({
                                "name": f"Расшифровка ключа {k['provider']} ({k['id'][:8]}...)",
                                "status": "ok",
                                "details": {
                                    "key_len": len(decrypted),
                                    "key_preview": decrypted[:20] + "..." if len(decrypted) > 20 else decrypted[:10]
                                }
                            })
                        else:
                            decrypt_errors.append(k["provider"])
                    except Exception as e:
                        decrypt_errors.append(f"{k['provider']}: {e}")

                if decrypt_errors:
                    result["steps"].append({
                        "name": "Проблемы расшифровки",
                        "status": "error",
                        "details": {"errors": decrypt_errors}
                    })
        else:
            result["steps"].append({
                "name": "API ключи",
                "status": "error",
                "details": {"error": "Database client not available"}
            })
    except Exception as e:
        error_msg = str(e)
        result["steps"].append({
            "name": "API ключи",
            "status": "error",
            "details": {"error": error_msg}
        })

    # Общий статус
    errors = [s for s in result["steps"] if s["status"] == "error"]
    warnings = [s for s in result["steps"] if s["status"] == "warning"]
    if errors:
        result["overall"] = "error"
    elif warnings:
        result["overall"] = "warning"
    else:
        result["overall"] = "ok"

    return result

