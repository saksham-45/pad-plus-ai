#!/usr/bin/env python3
"""
🔐 Генерация соли для шифрования

Использование:
    python scripts/generate_salt.py

Сохраните вывод в переменную окружения ENCRYPTION_SALT
"""

import base64
import os

# Генерируем случайную соль (32 байта)
salt = os.urandom(32)
salt_b64 = base64.urlsafe_b64encode(salt).decode()

print("=" * 60)
print("🔐 ENCRYPTION_SALT для шифрования API ключей")
print("=" * 60)
print()
print("Скопируйте это значение в .env или Render Dashboard:")
print()
print(f"ENCRYPTION_SALT={salt_b64}")
print()
print("=" * 60)
print("⚠️  ВАЖНО: Сохраните это значение!")
print("   При потере соли все зашифрованные ключи станут нечитаемыми")
print("=" * 60)
