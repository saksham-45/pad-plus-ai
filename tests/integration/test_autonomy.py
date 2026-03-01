"""
Тест улучшенной автономности
"""

import pytest
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

@pytest.mark.integration
@pytest.mark.autonomy
@pytest.mark.slow
def test_chat_with_quality():
    """Тест чата с самооценкой качества"""
    print("\n🧪 Тест чата с самооценкой...")
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"prompt": "Расскажи о себе кратко"}
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Ответ получен")
    print(f"   Provider: {data.get('provider')}")
    print(f"   Quality Score: {data.get('quality_score')}")
    print(f"   Quality Factors: {data.get('quality_factors')}")
    print(f"   Concepts Extracted: {data.get('concepts_extracted')}")
    print(f"   RAG Used: {data.get('rag_used')}")
    print(f"   Response: {data.get('response')[:100]}...")
    
    assert "provider" in data
    assert "response" in data
    assert len(data["response"]) > 0
    
    return data

@pytest.mark.integration
@pytest.mark.autonomy
def test_autonomy_status():
    """Тест статуса автономности"""
    print("\n🧪 Тест статуса автономности...")
    
    response = requests.get(f"{BASE_URL}/autonomy/status")
    assert response.status_code == 200
    data = response.json()
    
    print(f"✅ Статус получен")
    print(f"   Dialog Count: {data['planner']['dialog_count']}")
    print(f"   Pending Tasks: {data['planner']['pending_tasks']}")
    print(f"   Quality Stats: {data.get('quality', {})}")
    print(f"   Knowledge Extractions: {data.get('knowledge_extractions', 0)}")
    
    assert "planner" in data
    assert "dialog_count" in data["planner"]
    assert "pending_tasks" in data["planner"]
    
    return data

@pytest.mark.integration
@pytest.mark.autonomy
def test_multiple_chats():
    """Несколько чатов для тестирования авто-рефлексии"""
    print("\n🧪 Тестирование нескольких диалогов...")
    
    prompts = [
        "Что такое искусственный интеллект?",
        "Как работает нейронная сеть?",
        "Объясни машинное обучение"
    ]
    
    results = []
    for i, prompt in enumerate(prompts):
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"prompt": prompt}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"   Диалог {i+1}: quality={data.get('quality_score')}, concepts={data.get('concepts_extracted')}")
        results.append(data)
    
    assert len(results) == len(prompts)
    return results

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 ТЕСТ УЛУЧШЕННОЙ АВТОНОМНОСТИ")
    print("=" * 50)
    
    # Тестируем чат
    test_chat_with_quality()
    
    # Тестируем статус
    test_autonomy_status()
    
    # Несколько диалогов
    test_multiple_chats()
    
    # Финальный статус
    print("\n📊 Финальный статус:")
    status = test_autonomy_status()
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print("=" * 50)