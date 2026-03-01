"""
Тест подключения к Supabase
"""

import sys
import os

# Добавляем путь к backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.config_manager import test_database_connection


def main():
    """Основная функция теста"""
    print("🧪 Тест подключения к Supabase PostgreSQL")
    print("=" * 50)
    
    success = test_database_connection()
    
    print("=" * 50)
    if success:
        print("✅ Подключение к базе данных успешно!")
        print("🚀 PAD+ AI готов к работе с Supabase!")
    else:
        print("❌ Ошибка подключения к базе данных!")
        print("🔧 Проверьте:")
        print("   1. DATABASE_URL в переменных окружения")
        print("   2. Пароль от Supabase")
        print("   3. Доступность Supabase")


if __name__ == "__main__":
    main()
