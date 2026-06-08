"""
🔒 DEPRECATED — ИСПОЛЬЗУЙТЕ main.py ВМЕСТО ЭТОГО

Этот файл больше не используется в production (render.yaml → main:app).
Оставлен для отладки без Supabase/Redis.

Вся функциональность перенесена в:
- backend/api/frontend_routes.py (основные роуты)
- backend/core/ (авторизация через Supabase)
- backend/runtime/ (LLM сервисы)
"""

# === ОТКЛЮЧЕНИЕ ПРОКСИ ДЛЯ ВСЕХ API ЗАПРОСОВ ===
# Это предотвращает ошибки подключения через несуществующий прокси 127.0.0.1:12334
import os
# Удаляем все прокси переменные
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)
    os.environ.pop(proxy_var.lower(), None)
# Отключаем прокси для urllib
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import uvicorn
from datetime import datetime
import json
import asyncio
import aiohttp
import base64
import uuid
from pathlib import Path
import hashlib
import tempfile
import os
import sys

# fcntl только для Unix систем
if sys.platform != 'win32':
    import fcntl

# === ENCRYPTION для API ключей ===
_encryptor = None
def _get_encryptor():
    global _encryptor
    if _encryptor is None:
        try:
            from core.encryption import get_encryptor
            _encryptor = get_encryptor()
            logger.info("✅ Encryption loaded")
        except Exception as e:
            logger.warning(f"⚠️ Encryption not available: {e}")
            _encryptor = False
    return _encryptor

def _encrypt_key(key: str) -> str:
    """Шифрует API ключ"""
    enc = _get_encryptor()
    if enc:
        return enc.encrypt(key)
    return key

def _decrypt_key(encrypted_key: str) -> str:
    """Расшифровывает API ключ"""
    enc = _get_encryptor()
    if enc:
        return enc.decrypt(encrypted_key)
    return encrypted_key

# === СОХРАНЕНИЕ ДАННЫХ ===
DATA_DIR = os.getenv('DATA_DIR', str(Path(__file__).parent / "data"))
DATA_FILE = Path(DATA_DIR) / "stable_data.json"

def _hash(s: str) -> str:
    """Хеширует строку"""
    return hashlib.sha256(s.encode()).hexdigest()

def _is_hash(s: str) -> bool:
    """Проверяет, является ли строка хешем SHA256"""
    return len(s) == 64 and all(c in '0123456789abcdef' for c in s)

def _hash_password(password: str) -> str:
    """Хеширует пароль"""
    return _hash(password)

def load_data():
    """Загружает users_db и keys_db из JSON файла"""
    import main_stable
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                else:
                    data = json.load(f)
            
            loaded_users = data.get("users", {})
            loaded_keys = data.get("keys", {})
            
            main_stable.users_db = loaded_users
            main_stable.keys_db = loaded_keys
                
            logger.info(f"📂 Данные загружены: {len(loaded_users)} пользователей, {sum(len(v) for v in loaded_keys.values())} ключей")
        else:
            logger.info("📂 Файл данных не найден, используем пустую базу")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка чтения JSON: {e}. Начинаем с чистого листа.")
        main_stable.users_db = {}
        main_stable.keys_db = {}
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных: {e}")
        main_stable.users_db = {}
        main_stable.keys_db = {}

# База данных пользователей
users_db = {}  # Alias - use via module

# База данных API ключей  
keys_db = {}  # Alias - use via module

# Aliases for backward compatibility
def _get_users_db():
    import main_stable
    return main_stable.users_db

def _get_keys_db():
    import main_stable  
    return main_stable.keys_db

def save_data():
    """Сохраняет users_db и keys_db в JSON файл (атомарно, с блокировкой)"""
    import main_stable
    try:
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
        
        users_to_save = {}
        for email, user in main_stable.users_db.items():
            users_to_save[email] = user.copy()
            if "password" in users_to_save[user] and not _is_hash(users_to_save[user]["password"]):
                users_to_save[user]["password"] = _hash_password(users_to_save[user]["password"])
        
        data = {
            "users": users_to_save,
            "keys": main_stable.keys_db,
            "saved_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        # Атомарная запись через temp файл
        temp_path = DATA_FILE.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            if sys.platform != 'win32':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        os.replace(temp_path, DATA_FILE)
        logger.info(f"💾 Данные сохранены: {len(users_to_save)} пользователей, {sum(len(v) for v in main_stable.keys_db.values())} ключей")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных: {e}")

# Модели для запросов
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateKeyRequest(BaseModel):
    name: str
    provider: str
    api_key: str

class KeyUpdateRequest(BaseModel):
    name: str = None
    model_preference: str = None

class ChatRequest(BaseModel):
    message: str
    key_id: str = None
    provider: str = "gigachat"
    model: str = "auto"
    auto_mode: bool = False

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("padplus.stable")

# Создание FastAPI приложения
app = FastAPI(
    title="PAD+ AI Stable API",
    version="1.0.0",
    description="Стабильный API без зависимостей"
)

# Добавляем middleware для правильной кодировки
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Создаем кастомный JSON response с правильной кодировкой
def create_json_response(content, status_code=200):
    return JSONResponse(
        content=content,
        status_code=status_code,
        media_type="application/json; charset=utf-8"
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# АВТОРИЗАЦИЯ
# ============================================================================

@app.post("/api/v1/auth/register")
async def register(request: RegisterRequest):
    """Регистрация пользователя"""
    try:
        if request.email in users_db:
            return JSONResponse(
                status_code=400,
                content={"detail": "Пользователь уже существует"}
            )
        
        user_id = f"user_{len(users_db) + 1}"
        # Хешируем пароль перед сохранением
        users_db[request.email] = {
            "id": user_id,
            "email": request.email,
            "password": _hash_password(request.password),  # Хешируем!
            "name": request.name,
            "created_at": datetime.now().isoformat()
        }
        
        # Сохраняем после регистрации
        save_data()
        
        return {
            "message": "Пользователь успешно зарегистрирован",
            "user": {
                "id": user_id,
                "email": request.email,
                "name": request.name
            }
        }
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Вход в систему"""
    try:
        user = users_db.get(request.email)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Неверный email или пароль"}
            )
        
        stored_password = user.get("password", "")
        # Проверяем пароль - поддержка и хеша, и plaintext (legacy)
        input_hash = _hash_password(request.password)
        is_valid = (stored_password == input_hash) or (stored_password == request.password)
        
        if not is_valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Неверный email или пароль"}
            )
        
        # Генерируем простые токены (в реальном приложении - JWT)
        access_token = f"access_{user['id']}_{datetime.now().timestamp()}"
        refresh_token = f"refresh_{user['id']}_{datetime.now().timestamp()}"
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"]
            }
        }
    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

@app.post("/api/v1/auth/refresh")
async def refresh_token(x_refresh_token: str):
    """Обновление токена"""
    try:
        if not x_refresh_token.startswith("refresh_"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Неверный refresh токен"}
            )
        
        user_id = x_refresh_token.split("_")[1]
        # Находим пользователя по ID
        user = None
        for u in users_db.values():
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Пользователь не найден"}
            )
        
        # Генерируем новые токены
        access_token = f"access_{user_id}_{datetime.now().timestamp()}"
        refresh_token = f"refresh_{user_id}_{datetime.now().timestamp()}"
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    except Exception as e:
        logger.error(f"Ошибка обновления токена: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

@app.get("/api/v1/auth/me")
async def get_profile(authorization: str = None):
    """Получение профиля пользователя"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Требуется авторизация"}
            )
        
        token = authorization.replace("Bearer ", "")
        if not token.startswith("access_"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Неверный токен"}
            )
        
        user_id = token.split("_")[1]
        # Находим пользователя по ID
        user = None
        for u in users_db.values():
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Пользователь не найден"}
            )
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "created_at": user["created_at"]
        }
    except Exception as e:
        logger.error(f"Ошибка получения профиля: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

# ============================================================================
# API КЛЮЧИ
# ============================================================================

@app.get("/api/v1/keys")
async def get_keys(request: Request, offset: int = 0, limit: int = 100):
    """Получение API ключей пользователя"""
    try:
        authorization = request.headers.get("Authorization")
        logger.info(f"🔍 DEBUG: Authorization header: '{authorization}'")
        
        # Проверка авторизации
        if not authorization or not authorization.startswith("Bearer "):
            logger.error(f"❌ DEBUG: Authorization failed. Empty: {not authorization}, Starts with Bearer: {authorization.startswith('Bearer ') if authorization else False}")
            return JSONResponse(
                status_code=401,
                content={"detail": {"error": "authorization_required", "message": "Требуется авторизация"}}
            )
        
        token = authorization.replace("Bearer ", "")
        logger.info(f"🔍 DEBUG: Получен токен: {token}")
        
        # Проверяем что токен содержит user_id (более гибкая проверка)
        if "_" not in token or len(token.split("_")) < 2:
            logger.error(f"❌ DEBUG: Токен не прошел проверку. Parts: {len(token.split('_'))}")
            return JSONResponse(
                status_code=401,
                content={"detail": {"error": "authorization_required", "message": "Требуется авторизация"}}
            )
        
        # Правильно извлекаем user_id: access_user_1_timestamp -> user_1
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""
        logger.info(f"🔍 DEBUG: Извлечен user_id: {user_id}")
        
        # Получаем ключи пользователя
        user_keys = keys_db.get(user_id, [])
        
        # Убираем зашифрованный ключ из ответа
        safe_keys = []
        for key in user_keys[offset:offset + limit]:
            key_copy = key.copy()
            key_copy.pop("api_key_encrypted", None)
            key_copy.pop("api_key", None)  # На всякий случай
            safe_keys.append(key_copy)
        
        return safe_keys
    except Exception as e:
        logger.error(f"Ошибка получения ключей: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

@app.post("/api/v1/keys")
async def create_key(request: Request, key_request: CreateKeyRequest):
    """Создание API ключа"""
    try:
        # Проверка авторизации
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": {"error": "authorization_required", "message": "Требуется авторизация"}}
            )
        
        token = authorization.replace("Bearer ", "")
        # Правильно извлекаем user_id: access_user_1_timestamp -> user_1
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""
        
        # Создаем ключ
        key_id = f"key_{len(keys_db.get(user_id, [])) + 1}"
        encrypted = _encrypt_key(key_request.api_key)
        new_key = {
            "id": key_id,
            "name": key_request.name,
            "provider": key_request.provider,
            "api_key_encrypted": encrypted,  # Зашифрованный ключ
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        if user_id not in keys_db:
            keys_db[user_id] = []
        
        keys_db[user_id].append(new_key)
        
        # Сохраняем данные
        save_data()
        
        return new_key
    except Exception as e:
        logger.error(f"Ошибка создания ключа: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка сервера"}
        )

@app.post("/api/v1/keys/{key_id}/set-default")
async def set_default_key(request: Request, key_id: str):
    """Установка ключа по умолчанию"""
    try:
        # Проверка авторизации
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )

        token = authorization.replace("Bearer ", "")
        # Правильно извлекаем user_id: access_user_1_timestamp -> user_1
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""

        # Ищем и устанавливаем ключ по умолчанию
        if user_id in keys_db:
            user_keys = keys_db[user_id]
            key_found = False
            
            # Сбрасываем все ключи
            for key in user_keys:
                key["is_default"] = False
            
            # Устанавливаем новый ключ по умолчанию
            for key in user_keys:
                if key["id"] == key_id:
                    key["is_default"] = True
                    key_found = True
                    break
            
            if key_found:
                # Сохраняем данные
                save_data()
                return create_json_response({"message": "Ключ установлен по умолчанию", "key_id": key_id})
            else:
                return create_json_response({"detail": "API ключ не найден"}, status_code=404)
        else:
            return create_json_response({"detail": "API ключ не найден"}, status_code=404)
    except Exception as e:
        logger.error(f"Ошибка установки ключа по умолчанию: {e}")
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

@app.patch("/api/v1/keys/{key_id}")
async def update_key(request: Request, key_id: str, key_update: KeyUpdateRequest):
    """Обновление API ключа"""
    try:
        # Проверка авторизации
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )

        token = authorization.replace("Bearer ", "")
        # Правильно извлекаем user_id: access_user_1_timestamp -> user_1
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""

        # Ищем и обновляем ключ
        if user_id in keys_db:
            for key in keys_db[user_id]:
                if key["id"] == key_id:
                    # Обновляем поля
                    if key_update.name:
                        key["name"] = key_update.name
                    if key_update.model_preference:
                        key["model_preference"] = key_update.model_preference
                    key["updated_at"] = datetime.now().isoformat()
                    # Сохраняем данные
                    save_data()
                    return create_json_response({"message": "API ключ обновлен", "key": key})
            return create_json_response({"detail": "API ключ не найден"}, status_code=404)
        else:
            return create_json_response({"detail": "API ключ не найден"}, status_code=404)
    except Exception as e:
        logger.error(f"Ошибка обновления ключа: {e}")
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

@app.delete("/api/v1/keys/{key_id}")
async def delete_key(request: Request, key_id: str):
    """Удаление API ключа"""
    try:
        # Проверка авторизации
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )

        token = authorization.replace("Bearer ", "")
        # Правильно извлекаем user_id: access_user_1_timestamp -> user_1
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""

        # Ищем и удаляем ключ
        if user_id in keys_db:
            user_keys = keys_db[user_id]
            original_count = len(user_keys)
            keys_db[user_id] = [k for k in user_keys if k["id"] != key_id]

            if len(keys_db[user_id]) < original_count:
                # Сохраняем данные
                save_data()
                return create_json_response({"message": "API ключ успешно удален", "key_id": key_id})
            else:
                return create_json_response({"detail": "API ключ не найден"}, status_code=404)
        else:
            return create_json_response({"detail": "API ключ не найден"}, status_code=404)
    except Exception as e:
        logger.error(f"Ошибка удаления ключа: {e}")
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

# ============================================================================
# ОСНОВНЫЕ ЭНДПОИНТЫ
# ============================================================================

@app.get("/")
async def root():
    return {"message": "PAD+ AI Stable API работает", "status": "stable"}

@app.get("/api/v1/providers")
async def get_providers():
    """Список провайдеров"""
    return [
        {"id": "gigachat", "name": "GigaChat", "description": "Модели GigaChat от Сбера", "free_models": ["gigachat/GigaChat-2-Lite"]},
        {"id": "openai", "name": "OpenAI", "description": "Модели OpenAI", "free_models": []},
        {"id": "google", "name": "Google", "description": "Модели Google Gemini", "free_models": []},
        {"id": "anthropic", "name": "Anthropic", "description": "Модели Claude", "free_models": []},
        {"id": "cohere", "name": "Cohere", "description": "Модели Cohere", "free_models": []}
    ]

@app.get("/api/v1/providers/{provider_id}/models")
async def get_provider_models(provider_id: str):
    """Список моделей конкретного провайдера через LLMService"""
    try:
        # Используем LLMService для получения моделей
        from runtime.llm_service import get_llm_service
        
        llm_service = get_llm_service()
        models = llm_service.get_available_models(provider_id)
        
        # Если LLMService вернул модели - используем их
        if models:
            logger.info(f"✅ Получено {len(models)} актуальных моделей от {provider_id} через LLMService")
            return {"models": models}
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить модели через LLMService: {e}")
    
    # Fallback: базовый набор моделей если LLMService недоступен
    fallback_models = {
        "gigachat": [
            {"id": "gigachat/GigaChat", "name": "GigaChat", "max_tokens": 4096, "supports_vision": False},
            {"id": "gigachat/GigaChat-2-Lite", "name": "GigaChat 2 Lite", "max_tokens": 4096, "supports_vision": False},
            {"id": "gigachat/GigaChat-Pro", "name": "GigaChat Pro", "max_tokens": 8192, "supports_vision": False}
        ],
        "openai": [
            {"id": "gpt-4o", "name": "GPT-4o", "max_tokens": 128000, "supports_vision": True},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "max_tokens": 128000, "supports_vision": True},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "max_tokens": 128000, "supports_vision": True},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "max_tokens": 16385, "supports_vision": False}
        ],
        "google": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "max_tokens": 1048576, "supports_vision": True},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "max_tokens": 2097152, "supports_vision": True},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "max_tokens": 1048576, "supports_vision": True}
        ],
        "anthropic": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "max_tokens": 200000, "supports_vision": True},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "max_tokens": 200000, "supports_vision": True},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "max_tokens": 200000, "supports_vision": False}
        ],
        "cohere": [
            {"id": "command-r-plus", "name": "Command R+", "max_tokens": 128000, "supports_vision": False},
            {"id": "command-r", "name": "Command R", "max_tokens": 128000, "supports_vision": False}
        ],
        "groq": [
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "max_tokens": 131072, "supports_vision": False},
            {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B", "max_tokens": 131072, "supports_vision": False},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "max_tokens": 131072, "supports_vision": False}
        ],
        "deepseek": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "max_tokens": 128000, "supports_vision": False},
            {"id": "deepseek-coder", "name": "DeepSeek Coder", "max_tokens": 128000, "supports_vision": False}
        ],
        "openrouter": [
            {"id": "openrouter/gpt-4o-mini", "name": "GPT-4o Mini (OR)", "max_tokens": 128000, "supports_vision": True},
            {"id": "openrouter/gpt-4o", "name": "GPT-4o (OR)", "max_tokens": 128000, "supports_vision": True},
            {"id": "openrouter/anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (OR)", "max_tokens": 200000, "supports_vision": True},
            {"id": "openrouter/meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B (OR)", "max_tokens": 131072, "supports_vision": False},
            {"id": "openrouter/google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash Free", "max_tokens": 1048576, "supports_vision": True}
        ]
    }

    models = fallback_models.get(provider_id, [])
    logger.info(f"📦 Используем fallback список моделей для {provider_id}: {len(models)} моделей")
    return {"models": models}

@app.get("/api/v1/health")
async def health_check():
    """Проверка здоровья"""
    return {"status": "healthy", "backend": "stable", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/metrics/system")
async def get_system_metrics():
    """Метрики системы"""
    return {
        "cpu": 0,
        "memory": 0,
        "disk": 0,
        "network": 0,
        "uptime": 0,
        "requests": 0,
        "errors": 0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/models/metrics")
async def get_models_metrics():
    """Метрики моделей"""
    return {
        "models": [
            {
                "id": "gigachat",
                "name": "GigaChat",
                "status": "disabled",
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False
            },
            {
                "id": "gpt-4",
                "name": "GPT-4", 
                "status": "disabled",
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False
            },
            {
                "id": "claude",
                "name": "Claude",
                "status": "disabled", 
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False
            }
        ],
        "total_models": 3,
        "connected_models": 0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/metrics/activity")
async def get_activity():
    """Метрики активности"""
    return {
        "status": "ok",
        "active_users": len(users_db),
        "requests_today": 0,
        "errors": 0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/mind-state")
async def get_mind_state():
    """Состояние системы"""
    import main_stable
    
    # Подсчитываем метрики
    total_keys = sum(len(v) for v in main_stable.keys_db.values())
    active_keys = sum(
        sum(1 for k in keys if k.get("is_active", False))
        for keys in main_stable.keys_db.values()
    )
    
    return {
        "status": "stable",
        "mode": "minimal",
        "components": {
            "auth": "active",
            "api": "active",
            "database": "file",
            "cache": "disabled",
            "monitoring": "active",
            "rag": "disabled",

            "llm_service": "active"
        },
        "model": {
            "id": "auto",
            "name": "Auto (провайдер по умолчанию)",
            "provider": "default",
            "description": "Автоматический выбор модели"
        },
        # Метрики
        "memory": {
            "rag": {"total_dialogs": 0},
            "episodic": {"total": 0},
            "semantic": {"total": 0},
            "facts": {"total": 0},
            "roots": {"total": 0}
        },
        "knowledge": {
            "nodes": 0,
            "edges": 0,
            "density": 0,
            "avg_connections": 0
        },
        "health": {
            "overall_score": 0.0,
            "reflection": 0.0,
            "learning": 0.0,
            "adaptation": 0.0,
            "memory": 0.0,
            "coherence": 0.0,
            "quality": 0.0,
            "safety": 0.0,
            "balance": 0.0
        },
        "users": {
            "total": len(main_stable.users_db),
            "active": len(main_stable.users_db)
        },
        "keys": {
            "total": total_keys,
            "active": active_keys
        }
    }

@app.get("/api/v1/events/recent")
async def get_recent_events(limit: int = 20):
    """Последние события"""
    return {
        "events": [],
        "total": 0,
        "limit": limit,
        "message": "Events disabled in stable mode"
    }

@app.get("/api/v1/user/profile")
async def get_user_profile(request: Request):
    """Профиль пользователя"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )
        
        token = authorization.replace("Bearer ", "")
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""
        
        if user_id in users_db:
            user = users_db[user_id]
            return create_json_response({
                "id": user_id,
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"],
                "keys_count": len(keys_db.get(user_id, []))
            })
        else:
            return create_json_response({"detail": "Пользователь не найден"}, status_code=404)
    except Exception as e:
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

@app.get("/api/v1/analytics/usage")
async def get_usage_analytics(request: Request):
    """Аналитика использования"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )
        
        return create_json_response({
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "models_used": [],
            "daily_usage": [],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

@app.get("/api/v1/system/status")
async def get_system_status():
    """Статус системы"""
    return create_json_response({
        "status": "running",
        "mode": "stable",
        "uptime": 0,
        "version": "1.0.0",
        "components": {
            "database": "memory",
            "cache": "disabled",
            "ai_models": "disabled",
            "websocket": "active",
            "api": "active"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.get("/api/v1/models/list")
async def get_models_list():
    """Список моделей"""
    return create_json_response([
        {
            "id": "gigachat",
            "name": "GigaChat",
            "provider": "gigachat",
            "type": "chat",
            "status": "disabled",
            "description": "Модель GigaChat от Сбера"
        },
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "provider": "openai", 
            "type": "chat",
            "status": "disabled",
            "description": "Модель GPT-4 от OpenAI"
        },
        {
            "id": "claude-3",
            "name": "Claude 3",
            "provider": "anthropic",
            "type": "chat", 
            "status": "disabled",
            "description": "Модель Claude 3 от Anthropic"
        }
    ])

@app.post("/api/v1/models/test")
async def test_model(request: Request, model_test: dict):
    """Тест модели"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )
        
        model_id = model_test.get("model_id")
        return create_json_response({
            "model_id": model_id,
            "status": "disabled",
            "connected": False,
            "latency": 0,
            "error": "Модели отключены в стабильной версии",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return create_json_response({"detail": "Ошибка сервера"}, status_code=500)

@app.get("/api/v1/models/metrics")
async def get_models_metrics():
    """Метрики подключения моделей"""
    return {
        "models": [
            {
                "id": "gigachat",
                "name": "GigaChat",
                "status": "disabled",
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False,
                "reason": "Стабильная версия - AI отключены"
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "status": "disabled",
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False,
                "reason": "Стабильная версия - AI отключены"
            },
            {
                "id": "claude",
                "name": "Claude",
                "status": "disabled",
                "connected": False,
                "latency": 0,
                "requests": 0,
                "errors": 0,
                "last_used": None,
                "available": False,
                "reason": "Стабильная версия - AI отключены"
            }
        ],
        "total_models": 3,
        "connected_models": 0,
        "active_models": 0,
        "timestamp": datetime.now().isoformat(),
        "system_mode": "stable",
        "note": "В стабильной версии все AI модели отключены для надежности"
    }

@app.get("/api/v1/metrics/activity")
async def get_activity():
    """Метрики активности"""
    return {
        "status": "ok",
        "active_users": len(users_db),
        "requests_today": 0,
        "errors": 0
    }

@app.get("/api/v1/events/recent")
async def get_recent_events(limit: int = 20):
    """Получение последних событий"""
    # В стабильной версии возвращаем пустые данные
    return {
        "events": [],
        "total": 0,
        "limit": limit,
        "message": "Events disabled in stable mode"
    }

@app.post("/api/v1/chat")
async def chat(request: Request, chat_request: ChatRequest):
    """Обработка чата через LLMService"""
    try:
        # Проверка авторизации
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_json_response(
                {"detail": "Требуется авторизация"},
                status_code=401
            )
        
        token = authorization.replace("Bearer ", "")
        # Извлекаем user_id
        token_parts = token.split("_")
        if len(token_parts) >= 3:
            user_id = f"{token_parts[1]}_{token_parts[2]}"
        else:
            user_id = token_parts[1] if len(token_parts) > 1 else ""
        
        # Проверяем наличие API ключей
        user_keys = keys_db.get(user_id, [])
        if not user_keys:
            return create_json_response(
                {"detail": "Нет доступных API ключей. Добавьте ключ в настройках."},
                status_code=400
            )
        
        # Находим нужный ключ
        api_key = None
        provider = chat_request.provider or "gigachat"
        model = chat_request.model if chat_request.model and chat_request.model != "auto" else None
        
        if chat_request.key_id:
            for key in user_keys:
                if key["id"] == chat_request.key_id:
                    api_key = _decrypt_key(key.get("api_key_encrypted", key.get("api_key", "")))
                    provider = key["provider"]
                    if not model and key.get("model_preference"):
                        model = key["model_preference"]
                    break
        
        if not api_key:
            for key in user_keys:
                if key.get("is_default", False):
                    api_key = _decrypt_key(key.get("api_key_encrypted", key.get("api_key", "")))
                    provider = key["provider"]
                    if not model and key.get("model_preference"):
                        model = key["model_preference"]
                    break
            if not api_key and user_keys:
                api_key = _decrypt_key(user_keys[0].get("api_key_encrypted", user_keys[0].get("api_key", "")))
                provider = user_keys[0]["provider"]
                if not model and user_keys[0].get("model_preference"):
                    model = user_keys[0]["model_preference"]
        
        if not api_key:
            return create_json_response(
                {"detail": "Не удалось найти API ключ"},
                status_code=400
            )
        
        logger.info(f"🚀 Chat: provider={provider}, model={model}, message_length={len(chat_request.message)}")
        
        # === ИСПОЛЬЗУЕМ LLMService ДЛЯ ГЕНЕРАЦИИ ОТВЕТА ===
        try:
            from runtime.llm_service import get_llm_service
            
            llm_service = get_llm_service()
            
            # Выбираем модель если не указана
            if not model or model == "auto":
                # Дефолтные модели для провайдеров
                default_models = {
                    "gigachat": "gigachat/GigaChat",
                    "openai": "gpt-4o-mini",
                    "google": "gemini-2.0-flash",
                    "anthropic": "claude-3-5-haiku-20241022",
                    "groq": "llama-3.1-70b-versatile",
                    "deepseek": "deepseek-chat",
                    "cohere": "command-r",
                    "ollama": "llama3.2",
                    "openrouter": "openrouter/gpt-4o-mini",
                    "together_ai": "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    "mistral": "mistral/mistral-small-latest",
                    "xai": "xai/grok-2",
                    "azure": "azure/gpt-4o-mini",
                    "vertex_ai": "vertex_ai/gemini-2.0-flash"
                }
                model = default_models.get(provider, "gpt-4o-mini")
                
            # Корректируем формат модели для OpenRouter и других
            # Убираем дублирующий префикс если он уже есть
            if provider == "openrouter":
                if model.startswith("openrouter/openrouter/"):
                    model = model.replace("openrouter/openrouter/", "openrouter/")
                elif not model.startswith("openrouter/"):
                    model = f"openrouter/{model}"
            elif provider == "together_ai" and not model.startswith("together_ai/"):
                model = f"together_ai/{model}"
            elif provider == "mistral" and not model.startswith("mistral/"):
                model = f"mistral/{model}"
            elif provider == "xai" and not model.startswith("xai/"):
                model = f"xai/{model}"
            
            # Устанавливаем правильные API endpoints (переопределяем возможные неправильные значения из env)
            api_bases = {
                "openrouter": "https://openrouter.ai/api/v1",
                "together_ai": "https://api.together.xyz/v1",
                "groq": "https://api.groq.com/openai/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "mistral": "https://api.mistral.ai/v1",
                "xai": "https://api.x.ai/v1",
                "cohere": "https://api.cohere.ai/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "openai": "https://api.openai.com/v1",
                "google": None,  # Для Google используется отдельная библиотека
                "gigachat": "https://gigachat.devices.sberbank.ru/api/v1",
                "azure": None,  # Для Azure используется специальная конфигурация
                "vertex_ai": None  # Для Vertex AI используется специальная конфигурация
            }
            
            # Устанавливаем переменные окружения для провайдера
            api_base = api_bases.get(provider)
            if api_base:
                env_var_name = f"{provider.upper()}_API_BASE"
                os.environ[env_var_name] = api_base
                logger.info(f"🔧 Установлен {env_var_name}={api_base}")
            
            # Специальная обработка для OpenRouter - устанавливаем API ключ
            if provider == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = api_key
            
            # Генерируем ответ через LLMService
            ai_response = await llm_service.generate(
                prompt=chat_request.message,
                system_prompt="Вы полезный AI ассистент PAD+. Отвечайте на русском языке, будьте вежливы и конструктивны.",
                api_key=api_key,
                model=model,
                provider=provider
            )
            
            # Формируем ответ
            response = {
                "id": f"chat_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
                "message": ai_response.text,
                "text": ai_response.text,
                "response": ai_response.text,
                "provider": provider,
                "model": ai_response.model,
                "usage": ai_response.usage,
                "finish_reason": ai_response.finish_reason,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "is_fast_mode": True
            }
            
            # Обновляем last_used_at у ключа
            for key in user_keys:
                stored_key = key.get("api_key_encrypted", key.get("api_key", ""))
                if stored_key and _decrypt_key(stored_key) == api_key:
                    key["last_used_at"] = datetime.now().isoformat()
                    break
            
            logger.info(f"✅ Chat response: model={ai_response.model}, tokens={ai_response.usage}")
            
        except Exception as ai_error:
            logger.error(f"❌ AI generation error: {ai_error}")
            # Fallback: если AI упал - возвращаем ошибку с деталями
            return create_json_response(
                {
                    "detail": f"Ошибка генерации ответа: {str(ai_error)}",
                    "error_type": type(ai_error).__name__,
                    "provider": provider,
                    "model": model
                },
                status_code=502
            )
        
        return create_json_response(response)
    except Exception as e:
        logger.error(f"Ошибка чата: {e}")
        return create_json_response(
            {"detail": "Ошибка сервера"},
            status_code=500
        )

# ============================================================================
# WEBSOCKET
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт"""
    try:
        await manager.connect(websocket)
        logger.info("WebSocket клиент подключен")
        
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            logger.info(f"WebSocket получил: {message_data}")
            
            # Простой ответ
            response = {
                "type": "response",
                "message": f"Стабильный backend получил: {message_data.get('message', '')}",
                "timestamp": datetime.now().isoformat(),
                "status": "stable"
            }
            
            await manager.send_personal_message(json.dumps(response), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket клиент отключен")
    except Exception as e:
        logger.error(f"WebSocket ошибка: {e}")
        manager.disconnect(websocket)

# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    # Загружаем сохраненные данные
    load_data()
    
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Запуск стабильного backend на порту {port}")
    logger.info("📦 Компоненты отключены для стабильности")
    logger.info("✅ Авторизация и API работают")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
