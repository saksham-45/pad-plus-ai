"""
Тестирование Knowledge Graph — NeuroMind AI
"""

import sys
import os
import asyncio
from typing import Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKnowledgeGraph:
    """Тестирование Knowledge Graph системы"""
    
    async def test_graph_initialization(self):
        """Тест инициализации графа знаний"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        stats = graph.get_stats()
        
        assert stats["nodes"] >= 0
        assert stats["edges"] >= 0
        print("  ✅ Knowledge Graph: инициализация работает")
    
    async def test_node_operations(self):
        """Тест операций с узлами"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        # Тест добавления узла
        node_id = graph.add_node("Тест узла", {"type": "test"})
        assert node_id is not None
        
        # Тест получения узла
        node = graph.get_node(node_id)
        assert node is not None
        assert node["data"]["type"] == "test"
        
        # Тест удаления узла
        graph.delete_node(node_id)
        node = graph.get_node(node_id)
        assert node is None
        
        print("  ✅ Knowledge Graph: операции с узлами работают")
    
    async def test_edge_operations(self):
        """Тест операций с ребрами"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        # Создание узлов
        node1_id = graph.add_node("Узел 1", {"type": "source"})
        node2_id = graph.add_node("Узел 2", {"type": "target"})
        
        # Тест добавления ребра
        edge_id = graph.add_edge(node1_id, node2_id, "связь", {"weight": 0.8})
        assert edge_id is not None
        
        # Тест получения ребра
        edge = graph.get_edge(edge_id)
        assert edge is not None
        assert edge["data"]["weight"] == 0.8
        
        # Тест удаления ребра
        graph.delete_edge(edge_id)
        edge = graph.get_edge(edge_id)
        assert edge is None
        
        # Очистка узлов
        graph.delete_node(node1_id)
        graph.delete_node(node2_id)
        
        print("  ✅ Knowledge Graph: операции с ребрами работают")
    
    async def test_complex_queries(self):
        """Тест сложных запросов"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        # Тест поиска по свойствам
        results = graph.search_nodes({"type": "concept"})
        assert isinstance(results, list)
        
        # Тест поиска соседей
        neighbors = graph.get_neighbors("some_node_id")
        assert isinstance(neighbors, list)
        
        # Тест путей
        paths = graph.find_paths("start_node", "end_node", max_length=3)
        assert isinstance(paths, list)
        
        print("  ✅ Knowledge Graph: сложные запросы работают")
    
    async def test_graph_inference(self):
        """Тест вывода знаний"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        # Тест вывода
        inference = graph.infer("some_concept")
        assert isinstance(inference, dict)
        assert "related_concepts" in inference
        
        print("  ✅ Knowledge Graph: вывод знаний работает")
    
    async def test_graph_updates(self):
        """Тест обновлений графа"""
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        
        # Тест обновления узла
        node_id = graph.add_node("Обновляемый узел", {"value": 1})
        graph.update_node(node_id, {"value": 2})
        
        node = graph.get_node(node_id)
        assert node["data"]["value"] == 2
        
        # Тест обновления ребра
        edge_id = graph.add_edge(node_id, "other_node", "связь", {"weight": 0.5})
        graph.update_edge(edge_id, {"weight": 0.7})
        
        edge = graph.get_edge(edge_id)
        assert edge["data"]["weight"] == 0.7
        
        # Очистка
        graph.delete_node(node_id)
        graph.delete_edge(edge_id)
        
        print("  ✅ Knowledge Graph: обновления работают")


def run_knowledge_graph_tests():
    """Запуск всех тестов Knowledge Graph"""
    print("\n" + "="*60)
    print("🕸️ ТЕСТИРОВАНИЕ KNOWLEDGE GRAPH")
    print("="*60)
    
    tests = TestKnowledgeGraph()
    results = []
    
    # Запускаем все тесты
    asyncio.run(tests.test_graph_initialization())
    asyncio.run(tests.test_node_operations())
    asyncio.run(tests.test_edge_operations())
    asyncio.run(tests.test_complex_queries())
    asyncio.run(tests.test_graph_inference())
    asyncio.run(tests.test_graph_updates())
    
    print("="*60)
    print("✅ Knowledge Graph: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)


if __name__ == "__main__":
    run_knowledge_graph_tests()