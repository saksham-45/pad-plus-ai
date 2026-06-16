"""
🔐 Auth Manager - Улучшенная система аутентификации

Функции:
- Валидация JWT токенов
- Автоматическое обновление refresh_token
- Обработка истекших токенов
- Разделение ошибок аутентификации (401) и сервера (500)
"""

import logging
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Header, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("padplus.auth")


class AuthManager:
    """Менеджер аутентификации с улучшенной обработкой токенов"""
    
    def __init__(self):
        self.token_cache: Dict[str, Dict[str, Any]] = {}
    
    def validate_token_format(self, token: str) -> Tuple[bool, str]:
        """
        Проверяет формат JWT токена
        
        Returns:
            (валиден, сообщение об ошибке)
        """
        if not token:
            return False, "Токен не предоставлен"
        
        # JWT состоит из 3 частей разделенных точкой
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Неверный формат JWT токена"
        
        # Проверяем, что части содержат только допустимые символы
        jwt_pattern = r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$'
        if not re.match(jwt_pattern, token):
            return False, "Токен содержит недопустимые символы"
        
        return True, ""
    
    async def validate_and_refresh(
        self, 
        supabase_client: Any, 
        token: str,
        refresh_token: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        """
        Проверяет токен и при необходимости обновляет
        
        Args:
            supabase_client: Клиент Supabase
            token: Access токен
            refresh_token: Refresh токен (опционально)
        
        Returns:
            (пользователь, новый_access_токен, ошибка)
        """
        if not supabase_client:
            return None, None, "БД не подключена"
        
        # 1. Проверяем формат токена
        is_valid, error_msg = self.validate_token_format(token)
        if not is_valid:
            return None, None, error_msg
        
        try:
            # 2. Пытаемся получить пользователя
            user_response = supabase_client.auth.get_user(token)
            
            if user_response and hasattr(user_response, 'user') and user_response.user:
                # Токен валиден - возвращаем только пользователя (без session)
                return {"user": user_response.user}, None, ""
        except Exception as auth_error:
            logger.warning(f"Ошибка get_user: {type(auth_error).__name__}: {auth_error}")
            # Продолжаем - попробуем обновить токен
            
            # 3. Если токен истек, пытаемся обновить
            if refresh_token:
                try:
                    refresh_response = supabase_client.auth.refresh_session(refresh_token)
                    
                    if refresh_response and hasattr(refresh_response, 'session') and refresh_response.session:
                        new_token = refresh_response.session.access_token
                        
                        # Пробуем еще раз с новым токеном
                        user_response = supabase_client.auth.get_user(new_token)
                        
                        if user_response and hasattr(user_response, 'user') and user_response.user:
                            return {"user": user_response.user}, new_token, ""
                        
                except Exception as refresh_error:
                    logger.warning(f"Не удалось обновить токен: {refresh_error}")
                    return None, None, "Неверный refresh токен"
            
            return None, None, "Токен истек или невалиден"
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Логируем детали для отладки
            logger.error(f"Ошибка аутентификации: {error_type}: {error_msg}")
            
            # Различаем типы ошибок
            if "InvalidCredentials" in error_type or "AuthError" in error_type:
                return None, None, "Неверные учетные данные"
            elif "NetworkError" in error_type or "ConnectionError" in error_type:
                return None, None, "Ошибка подключения к серверу аутентификации"
            else:
                return None, None, f"Ошибка аутентификации: {error_msg}"
    
    def extract_token_from_header(self, authorization: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Извлекает access и refresh токены из заголовка Authorization
        
        Поддерживаемые форматы:
        - "Bearer <access_token>"
        - "Bearer <access_token> <refresh_token>"
        
        Returns:
            (access_token, refresh_token)
        """
        if not authorization:
            return None, None
        
        if not authorization.startswith("Bearer "):
            return None, None
        
        # Убираем "Bearer "
        token_part = authorization[7:].strip()
        
        # Разделяем по пробелу для получения refresh_token
        parts = token_part.split()
        
        access_token = parts[0] if len(parts) >= 1 else None
        refresh_token = parts[1] if len(parts) >= 2 else None
        
        return access_token, refresh_token


# Глобальный экземпляр
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Получает глобальный экземпляр AuthManager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# ============================================================================
# ДЕКОРАТОРЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

async def get_current_user_safe(
    authorization: Optional[str] = Header(None),
    x_refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token")
) -> Dict[str, Any]:
    """
    Улучшенная версия get_current_user с обработкой refresh_token
    
    Используется в маршрутах вместо стандартного get_current_user
    """
    from core.supabase_client import get_supabase
    
    auth_manager = get_auth_manager()
    supabase = get_supabase()
    
    # 1. Проверяем наличие заголовка Authorization
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "authorization_required",
                "message": "Требуется заголовок Authorization"
            }
        )
    
    # 2. Извлекаем токены
    access_token, refresh_token = auth_manager.extract_token_from_header(authorization)
    
    if not access_token:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "invalid_token_format",
                "message": "Неверный формат заголовка Authorization. Ожидается: Bearer <token>"
            }
        )
    
    # Если refresh_token не передан в заголовке, пробуем взять из тела токена
    if not refresh_token:
        refresh_token = x_refresh_token
    
    # 3. Проверяем подключение к БД
    if not supabase:
        logger.error("БД не подключена при попытке аутентификации")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "database_unavailable",
                "message": "База данных недоступна"
            }
        )
    
    # 4. Валидируем и при необходимости обновляем токен
    auth_data, new_access_token, error = await auth_manager.validate_and_refresh(
        supabase, access_token, refresh_token
    )
    
    if not auth_data:
        # Определяем тип ошибки
        if "истек" in error.lower() or "невалиден" in error.lower():
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "token_expired",
                    "message": "Токен истек. Пожалуйста, войдите заново.",
                    "requires_login": True
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        elif "неверный refresh токен" in error.lower():
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_refresh_token",
                    "message": "Неверный refresh токен. Пожалуйста, войдите заново.",
                    "requires_login": True
                }
            )
        else:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "authentication_failed",
                    "message": f"Ошибка аутентификации: {error}"
                }
            )
    
    # 5. Получаем профиль пользователя
    user = auth_data["user"]
    
    try:
        profile_response = supabase.table("users")\
            .select("*")\
            .eq("id", user.id)\
            .execute()
        
        profile = profile_response.data[0] if profile_response.data else None
        
    except Exception as e:
        logger.error(f"Ошибка получения профиля: {e}")
        # Не блокируем запрос, если профиль не найден
        profile = None
    
    # 6. Формируем результат
    result = {
        "auth_user": user,
        "profile": profile,
        "id": user.id,
        "email": user.email
    }
    
    # Добавляем новый токен, если он был обновлен
    if new_access_token:
        result["new_access_token"] = new_access_token
    
    return result


def auth_required(f):
    """Декоратор для обязательной аутентификации"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        # Получаем текущий контекст (если вызывается из маршрута)
        from fastapi import Request
        
        # Если функция принимает request
        if 'request' in kwargs or len(args) > 0 and isinstance(args[0], Request):
            request = kwargs.get('request') or args[0]
            authorization = request.headers.get('Authorization')
            
            if not authorization:
                raise HTTPException(
                    status_code=401,
                    detail="Требуется аутентификация"
                )
            
            # Используем безопасную аутентификацию
            current_user = await get_current_user_safe(authorization)
            
            # Добавляем current_user в kwargs
            kwargs['current_user'] = current_user
        
        return await f(*args, **kwargs)
    return wrapper


# ============================================================================
# MIDDLEWARE ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ ТОКЕНА
# ============================================================================

class AuthRefreshMiddleware:
    """Middleware для автоматического добавления обновленного токена в ответ"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Проверяем, есть ли в запросе новый токен
        new_token = getattr(request.state, 'new_access_token', None)
        
        if new_token:
            # Добавляем новый токен в заголовок ответа
            response.headers['X-New-Access-Token'] = new_token
        
        return response


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Извлекает user_id из JWT токена без валидации
    Используется для логирования и отладки
    
    ВНИМАНИЕ: Не используйте для авторизации!
    """
    import base64
    import json
    
    try:
        # Разбираем JWT
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Декодируем payload (вторая часть)
        payload_bytes = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload_json = base64.urlsafe_b64decode(payload_bytes)
        payload = json.loads(payload_json)
        
        # Извлекаем sub (user_id)
        return payload.get('sub')
        
    except Exception as e:
        logger.warning(f"Не удалось извлечь user_id из токена: {e}")
        return None