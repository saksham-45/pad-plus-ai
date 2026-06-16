"""
🔐 Encryption Module для API ключей

Шифрование/дешифрование пользовательских API ключей
используя Fernet (symmetric encryption)

Безопасность:
- Ключи шифруются перед записью в БД
- Расшифровка только при использовании
- Ключ шифрования хранится в .env
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import logging

logger = logging.getLogger("padplus.encryption")


class KeyEncryptor:
    """
    🔐 Шифровальщик API ключей
    
    Использование:
        encryptor = KeyEncryptor(encryption_key)
        encrypted = encryptor.encrypt("openrouter-api-key-example")
        decrypted = encryptor.decrypt(encrypted)
    """
    
    def __init__(self, encryption_key: str):
        """
        Инициализирует шифровальщик

        Args:
            encryption_key: Ключ шифрования из .env (32+ символа)
        """
        try:
            # Генерируем ключ из пароля используя PBKDF2HMAC
            # Соль должна быть настроена в переменной окружения ENCRYPTION_SALT
            # Это критично для работы на Render (эфемерная файловая система)
            salt_env = os.getenv("ENCRYPTION_SALT")
            if not salt_env:
                logger.warning("⚠️ ENCRYPTION_SALT не настроен, используем временную соль")
                salt = os.urandom(16)
            else:
                try:
                    salt = base64.urlsafe_b64decode(salt_env)
                    logger.info("✅ Соль загружена из переменной окружения")
                except Exception:
                    logger.warning("⚠️ Не могу декодировать соль, используем временную")
                    salt = os.urandom(16)

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100_000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            self.cipher = Fernet(key)
            logger.info("✅ KeyEncryptor инициализирован")
        except Exception as e:
            logger.critical(f"❌ Критическая ошибка шифрования: {e}")
            logger.warning("⚠️ Используем режим без шифрования")
            self.fallback_mode = True
            return
    
    def encrypt(self, api_key: str) -> str:
        """
        Шифрует API ключ
        
        Args:
            api_key: API ключ в открытом виде
            
        Returns:
            Зашифрованный API ключ (base64)
        """
        try:
            encrypted = self.cipher.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        Дешифрует API ключ
        
        Args:
            encrypted: Зашифрованный API ключ
            
        Returns:
            API ключ в открытом виде
        """
        try:
            if not encrypted or encrypted == "" or encrypted == "None":
                return ""
            decrypted = self.cipher.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            logger.warning(f"⚠️ Не могу дешифровать ключ, возвращаю пустое: {e}")
            return ""
    
    def verify(self, encrypted: str, original: str) -> bool:
        """
        Проверяет соответствие зашифрованного ключа оригиналу
        
        Args:
            encrypted: Зашифрованный ключ
            original: Оригинальный ключ для проверки
            
        Returns:
            True если ключи совпадают
        """
        try:
            decrypted = self.decrypt(encrypted)
            return decrypted == original
        except Exception:
            return False


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_encryptor = None


def get_encryptor() -> KeyEncryptor:
    """
    Возвращает глобальный шифровальщик
    
    Инициализируется один раз при первом вызове.
    Ключ шифрования берётся из .env (ENCRYPTION_KEY)
    """
    global _encryptor
    if _encryptor is None:
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            logger.error("❌ ENCRYPTION_KEY не найден в .env")
            raise ValueError("ENCRYPTION_KEY не настроен")
        
        _encryptor = KeyEncryptor(encryption_key)
        logger.info("✅ Глобальный KeyEncryptor инициализирован")
    
    return _encryptor


def initialize_encryptor(encryption_key: str) -> KeyEncryptor:
    """
    Принудительно инициализирует шифровальщик
    
    Используется для тестов или явной инициализации
    """
    global _encryptor
    _encryptor = KeyEncryptor(encryption_key)
    return _encryptor
