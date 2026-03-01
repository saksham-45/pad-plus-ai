import os
import sys

# Устанавливаем переменную окружения
os.environ['DATABASE_URL'] = 'postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres'

# Импортируем и тестируем
from backend.core.config_manager import test_database_connection

# Запускаем тест
test_database_connection()
