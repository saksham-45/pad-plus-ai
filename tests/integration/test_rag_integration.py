"""Тест RAG функциональности"""
import httpx
import time
import pytest

BASE_URL = "http://localhost:8000/api/v1"


def _is_server_available():
    """Проверяет доступность сервера"""
    try:
        response = httpx.get(f"{BASE_URL}/chat", timeout=2)
        return True
    except Exception:
        return False


def test_chat():
    """Тестирует чат и сохранение в RAG"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("🧪 Тест чата с RAG...")
    
    # Отправляем сообщение
    response = httpx.post(
        f"{BASE_URL}/chat",
        json={"prompt": "Что такое искусственный интеллект?"},
        timeout=30.0
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Ответ: {data['response'][:100]}...")
        print(f"   Provider: {data['provider']}")
        print(f"   RAG использован: {data.get('rag_used', False)}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        return False
    
    return True

def test_rag_stats():
    """Проверяет статистику RAG"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n📊 Статистика RAG...")
    
    response = httpx.get(f"{BASE_URL}/rag/stats")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Диалогов в памяти: {data['total_dialogs']}")
        if 'encoder' in data:
            print(f"   Энкодер: {data['encoder']}")
        else:
            print("   Энкодер: не указан")
        return data['total_dialogs']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        return 0

def test_rag_search():
    """Тестирует семантический поиск"""
    if not _is_server_available():
        pytest.skip("Сервер не запущен на localhost:8000")
    print("\n🔍 Семантический поиск...")
    
    response = httpx.post(
        f"{BASE_URL}/rag/search",
        json={"query": "интеллект", "n_results": 3}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Найдено: {data['total']} результатов")
        for r in data['results']:
            print(f"   - Схожесть: {r['similarity']}")
        return data['total']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        return 0

if __name__ == "__main__":
    print("=" * 50)
    print("🧠 Тестирование RAG для NeuroMind AI")
    print("=" * 50)
    
    # Статистика до
    count_before = test_rag_stats()
    
    # Отправляем несколько сообщений
    test_chat()
    time.sleep(1)
    
    # Статистика после
    count_after = test_rag_stats()
    
    # Поиск
    if count_after > 0:
        test_rag_search()
    
    print("\n" + "=" * 50)
    if count_after > count_before:
        print("✅ RAG работает! Диалоги сохраняются.")
    else:
        print("⚠️ Диалоги не сохраняются в RAG")
    print("=" * 50)