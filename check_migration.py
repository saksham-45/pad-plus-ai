"""
Проверка миграции: наличие полей tags и summary в таблице documents
"""
import os
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("❌ Ошибка: SUPABASE_URL или SUPABASE_SERVICE_KEY не настроены в .env")
    exit(1)

print(f"🔗 Подключение к: {url}")

try:
    supabase = create_client(url, key)
    
    # Пробуем запросить поля tags и summary
    result = supabase.table("documents").select("tags,summary").limit(1).execute()
    
    if result.data is not None:
        print("✅ Миграция применена!")
        print("   Поля 'tags' и 'summary' существуют в таблице documents")
    else:
        print("⚠️ Таблица documents пуста, но поля существуют")
        print("✅ Миграция применена!")
        
except Exception as e:
    error_msg = str(e)
    if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
        print("❌ Миграция НЕ применена!")
        print(f"   Ошибка: {error_msg}")
        print("\n📋 Примени миграцию:")
        print("   1. Открой https://supabase.com/dashboard")
        print("   2. SQL Editor → New query")
        print("   3. Вставь:")
        print("      ALTER TABLE documents ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';")
        print("      ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;")
        print("   4. Нажми Run")
    else:
        print(f"❌ Неизвестная ошибка: {error_msg}")
