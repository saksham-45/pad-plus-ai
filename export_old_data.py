#!/usr/bin/env python3
"""
📤 Скрипт для экспорта данных из старой базы
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("Экспорт данных из старой базы")
print("=" * 60)

# Конфигурация
OLD_DB_URL = "postgresql://postgres.hgjbjccpeirwrabbcjhr:TiMuPom13Q5OfKBi@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"
NEW_DB_URL = "postgresql://postgres.uixqufwbxefvkmhmausm:i8Edeq5rosD8sAeV@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"

# Экспорт эпизодов
print("\n1. Экспорт эпизодов...")
try:
    import psycopg2
    
    # Подключение к старой базе
    old_conn = psycopg2.connect(OLD_DB_URL)
    old_cur = old_conn.cursor()
    
    # Получение всех эпизодов
    old_cur.execute("SELECT * FROM episodes")
    episodes = old_cur.fetchall()
    
    # Сохранение в JSON
    episodes_data = []
    for ep in episodes:
        episodes_data.append({
            "id": ep[0],
            "timestamp": str(ep[1]) if ep[1] else None,
            "user_id": ep[2],
            "situation": ep[3],
            "participants": ep[4],
            "location": ep[5],
            "user_message": ep[6],
            "ai_response": ep[7],
            "intent": ep[8],
            "topic": ep[9],
            "emotion_before": ep[10],
            "emotion_after": ep[11],
            "emotion_impact": float(ep[12]) if ep[12] is not None else 0.0,
            "entities": ep[13],
            "concepts": ep[14],
            "keywords": ep[15],
            "related_episodes": ep[16],
            "parent_episode": ep[17],
            "continuation_of": ep[18],
            "significance": float(ep[19]) if ep[19] is not None else 0.5,
            "access_count": int(ep[20]) if ep[20] is not None else 0,
            "last_accessed": str(ep[21]) if ep[21] else None,
            "duration_seconds": float(ep[22]) if ep[22] is not None else 0.0,
            "success": bool(ep[23]) if ep[23] is not None else True,
            "feedback": ep[24]
        })
    
    old_cur.close()
    old_conn.close()
    
    print(f"   Экспортировано: {len(episodes_data)} эпизодов")
    
    # Сохранение в файл
    with open('exported_episodes.json', 'w', encoding='utf-8') as f:
        json.dump(episodes_data, f, indent=2, ensure_ascii=False)
    
    print("   Сохранено в: exported_episodes.json")
    
except Exception as e:
    print(f"   Ошибка: {str(e)}")
    episodes_data = []

# Экспорт знаний
print("\n2. Экспорт знаний...")
try:
    import psycopg2
    
    # Подключение к старой базе
    old_conn = psycopg2.connect(OLD_DB_URL)
    old_cur = old_conn.cursor()
    
    # Получение всех знаний
    old_cur.execute("SELECT * FROM semantic_knowledge")
    knowledge = old_cur.fetchall()
    
    # Сохранение в JSON
        knowledge_data = []
    for kn in knowledge:
        knowledge_data.append({
            "id": kn[0],
            "content": kn[1],
            "knowledge_type": kn[2],
            "summary": kn[3],
            "confidence": float(kn[4]) if kn[4] is not None else 0.7,
            "domain": kn[5],
            "entities": kn[6],
            "concepts": kn[7],
            "related_knowledge": kn[8],
            "access_count": int(kn[9]) if kn[9] is not None else 0,
            "last_accessed": str(kn[10]) if kn[10] else None,
            "created_at": str(kn[11]) if kn[11] else None
        })
    
    old_cur.close()
    old_conn.close()
    
    print(f"   Экспортировано: {len(knowledge_data)} знаний")
    
    # Сохранение в файл
    with open('exported_knowledge.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_data, f, indent=2, ensure_ascii=False)
    
    print("   Сохранено в: exported_knowledge.json")
    
except Exception as e:
    print(f"   Ошибка: {str(e)}")
    knowledge_data = []

# Импорт в новую базу
print("\n3. Импорт в новую базу...")

if episodes_data:
    try:
        # Подключение к новой базе
        new_conn = psycopg2.connect(NEW_DB_URL)
        new_cur = new_conn.cursor()
        
        # Очистка таблиц
        new_cur.execute("DELETE FROM episodes")
        new_cur.execute("DELETE FROM episode_relations")
        
        # Вставка эпизодов
        for ep in episodes_data:
            new_cur.execute(
                "INSERT INTO episodes (id, timestamp, user_id, situation, participants, location, user_message, ai_response, intent, topic, emotion_before, emotion_after, emotion_impact, entities, concepts, keywords, related_episodes, parent_episode, continuation_of, significance, access_count, last_accessed, duration_seconds, success, feedback) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    ep["id"], ep["timestamp"], ep["user_id"], ep["situation"], json.dumps(ep["participants"]), ep["location"],
                    ep["user_message"], ep["ai_response"], ep["intent"], ep["topic"], json.dumps(ep["emotion_before"]),
                    json.dumps(ep["emotion_after"]), ep["emotion_impact"], json.dumps(ep["entities"]), json.dumps(ep["concepts"]), json.dumps(ep["keywords"]),
                    json.dumps(ep["related_episodes"]), ep["parent_episode"], ep["continuation_of"], ep["significance"],
                    ep["access_count"], ep["last_accessed"], ep["duration_seconds"], ep["success"], json.dumps(ep["feedback"])
                )
            )
        
        new_conn.commit()
        print(f"   Импортировано: {len(episodes_data)} эпизодов")
        
        new_cur.close()
        new_conn.close()
        
    except Exception as e:
        print(f"   Ошибка импорта эпизодов: {str(e)}")

if knowledge_data:
    try:
        # Подключение к новой базе
        new_conn = psycopg2.connect(NEW_DB_URL)
        new_cur = new_conn.cursor()
        
        # Очистка таблиц
        new_cur.execute("DELETE FROM semantic_knowledge")
        
        # Вставка знаний
        for kn in knowledge_data:
            new_cur.execute(
                "INSERT INTO semantic_knowledge (id, content, knowledge_type, summary, confidence, domain, entities, concepts, related_knowledge, access_count, last_accessed, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    kn["id"], kn["content"], kn["knowledge_type"], kn["summary"], kn["confidence"], kn["domain"],
                    json.dumps(kn["entities"]), json.dumps(kn["concepts"]), json.dumps(kn["related_knowledge"]), kn["access_count"], kn["last_accessed"], kn["created_at"]
                )
            )
        
        new_conn.commit()
        print(f"   Импортировано: {len(knowledge_data)} знаний")
        
        new_cur.close()
        new_conn.close()
        
    except Exception as e:
        print(f"   Ошибка импорта знаний: {str(e)}")

# Проверка
print("\n4. Проверка...")
try:
    # Подключение к новой базе
    new_conn = psycopg2.connect(NEW_DB_URL)
    new_cur = new_conn.cursor()
    
    # Проверка эпизодов
    new_cur.execute("SELECT COUNT(*) FROM episodes")
    new_episodes_count = new_cur.fetchone()[0]
    
    # Проверка знаний
    new_cur.execute("SELECT COUNT(*) FROM semantic_knowledge")
    new_knowledge_count = new_cur.fetchone()[0]
    
    new_cur.close()
    new_conn.close()
    
    print(f"   Эпизоды в новой базе: {new_episodes_count}")
    print(f"   Знания в новой базе: {new_knowledge_count}")
    
    if new_episodes_count == len(episodes_data) and new_knowledge_count == len(knowledge_data):
        print("\n✅ Перенос данных завершен успешно!")
        print("Все данные из старой базы перенесены в новую.")
    else:
        print("\n⚠️  Перенос завершен с ошибками")
        print("Не все данные были перенесены.")
        
except Exception as e:
    print(f"   Ошибка проверки: {str(e)}")

print("\n" + "=" * 60)
print("Следующие шаги:")
print("=" * 60)
print("1. Обновите DATABASE_URL в Render на новую базу")
print("2. Сделайте редеплой в Render")
print("3. Проверьте, что метрики отображаются")
print("4. Удалите старую базу (если не нужна)")