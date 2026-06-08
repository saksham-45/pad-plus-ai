#!/usr/bin/env python3
"""
Скрипт для проверки RLS политик в Supabase
Требуется: pip install supabase python-dotenv
"""

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Ошибка: Не найдены SUPABASE_URL и SUPABASE_KEY в .env")
    exit(1)

try:
    from supabase import create_client
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Проверяем политики
    response = supabase.postgrest.query(
        "SELECT policyname, cmd, qual, with_check FROM pg_policies WHERE tablename = 'user_api_keys' ORDER BY policyname"
    )
    
    print("📋 Текущие RLS политики для user_api_keys:")
    print("-" * 80)
    
    if response.data:
        for policy in response.data:
            print(f"\n✓ {policy['policyname']}")
            print(f"  Операция: {policy['cmd']}")
            print(f"  USING: {policy['qual'][:100] if policy['qual'] else 'нет'}")
            print(f"  WITH CHECK: {policy['with_check'][:100] if policy['with_check'] else 'нет'}")
    else:
        print("❌ Политик НЕ найдено! Нужно их создать.")
        print("\nВыполните SQL из DIAGNOSTIC.md")
    
    print("\n" + "-" * 80)
    
except ImportError:
    print("⚠️  Supabase клиент не установлен.")
    print("Установите: pip install supabase")
    exit(1)
except Exception as e:
    print(f"❌ Ошибка проверки: {e}")
    exit(1)
