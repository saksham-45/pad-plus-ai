"""
Тест RAG v3.0

- LLM-суммаризация
- Классификация тем диалогов
- Извлечение сущностей и связей
"""

import requests
import json
import pytest

BASE_URL = "http://localhost:8000/api/v1"


def _is_server_available():
    """Проверяет доступность сервера"""
    try:
        response = requests.get(f"{BASE_URL}/rag/stats", timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def test_rag_stats():
    """Тест статистики RAG v3.0"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест статистики RAG v3.0...")
    
    response = requests.get(f"{BASE_URL}/rag/stats")
    data = response.json()
    
    print(f"✅ Статистика получена")
    print(f"   Version: {data.get('version')}")
    print(f"   Total Dialogs: {data.get('total_dialogs')}")
    print(f"   Total Entities: {data.get('total_entities')}")
    print(f"   Total Relations: {data.get('total_relations')}")
    print(f"   Topics: {data.get('topic_distribution')}")
    print(f"   Sentiment: {data.get('sentiment_distribution')}")
    print(f"   Features: {list(data.get('features', {}).keys())}")
    
    return data


def test_chat_with_analysis():
    """Тест чата с анализом темы и сущностей"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест чата с анализом...")
    
    prompts = [
        "Что такое Python и как он используется в машинном обучении?",
        "Объясни разницу между React и Vue",
        "Как работает нейронная сеть?"
    ]
    
    for prompt in prompts:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"prompt": prompt}
        )
        data = response.json()
        print(f"   Prompt: {prompt[:50]}...")
        print(f"   Quality: {data.get('quality_score')}")
        print(f"   Concepts: {data.get('concepts_extracted')}")
    
    return True


def test_topics():
    """Тест получения тем"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест тем диалогов...")
    
    response = requests.get(f"{BASE_URL}/rag/topics")
    data = response.json()
    
    print(f"✅ Темы получены")
    print(f"   Total Topics: {data.get('total_topics')}")
    for topic, count in data.get('topics', {}).items():
        print(f"   - {topic}: {count}")
    
    return data


def test_entities():
    """Тест индекса сущностей"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест сущностей...")
    
    response = requests.get(f"{BASE_URL}/rag/entities")
    data = response.json()
    
    print(f"✅ Сущности получены")
    print(f"   Total Entities: {data.get('total_entities')}")
    
    # Показываем несколько сущностей
    entities = data.get('entities', {})
    for entity, docs in list(entities.items())[:5]:
        print(f"   - {entity}: {len(docs)} документов")
    
    return data


def test_hybrid_search():
    """Тест гибридного поиска"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест гибридного поиска...")
    
    response = requests.post(
        f"{BASE_URL}/rag/hybrid",
        json={
            "query": "машинное обучение",
            "n_results": 3,
            "use_keywords": True,
            "use_recency": True
        }
    )
    data = response.json()
    
    print(f"✅ Поиск выполнен")
    print(f"   Query: {data.get('query')}")
    print(f"   Total Results: {data.get('total')}")
    
    for i, result in enumerate(data.get('results', [])[:3], 1):
        print(f"\n   Result {i}:")
        print(f"     Topic: {result.get('topic')}")
        print(f"     Sentiment: {result.get('sentiment')}")
        print(f"     Score: {result.get('combined_score')}")
        entities = result.get('entities', [])
        if entities:
            print(f"     Entities: {[e['value'] for e in entities[:3]]}")
    
    return data


def test_search_by_topic():
    """Тест поиска по теме"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🧪 Тест поиска по теме...")
    
    response = requests.post(
        f"{BASE_URL}/rag/by-topic",
        json={"topic": "техническое", "n_results": 3}
    )
    data = response.json()
    
    print(f"✅ Поиск по теме выполнен")
    print(f"   Topic: {data.get('topic')}")
    print(f"   Total: {data.get('total')}")
    
    return data


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ТЕСТ RAG v3.0")
    print("=" * 60)
    
    # Тестируем
    test_chat_with_analysis()
    test_rag_stats()
    test_topics()
    test_entities()
    test_hybrid_search()
    test_search_by_topic()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование RAG v3.0 завершено!")
    print("=" * 60)