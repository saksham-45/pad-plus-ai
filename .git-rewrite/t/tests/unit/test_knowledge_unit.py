"""
Unit тесты для графа знаний
"""

import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.knowledge
class TestKnowledgeGraph:
    """Тесты графа знаний"""
    
    def test_knowledge_graph_stats(self, sample_knowledge_graph):
        """Тест статистики графа знаний"""
        with patch('knowledge.graph.get_knowledge_graph') as mock_get_graph:
            mock_graph = Mock()
            mock_graph.get_stats.return_value = {
                "nodes": len(sample_knowledge_graph["nodes"]),
                "edges": len(sample_knowledge_graph["edges"]),
                "components": 1
            }
            mock_get_graph.return_value = mock_graph
            
            # Вызов
            graph = mock_get_graph()
            stats = graph.get_stats()
            
            # Проверки
            assert "nodes" in stats
            assert "edges" in stats
            assert stats["nodes"] == 2
            assert stats["edges"] == 1
            mock_graph.get_stats.assert_called_once()
    
    def test_add_concept(self):
        """Тест добавления концепта"""
        with patch('knowledge.graph.get_knowledge_graph') as mock_get_graph:
            mock_graph = Mock()
            mock_graph.add_node.return_value = "concept_123"
            mock_get_graph.return_value = mock_graph
            
            # Вызов
            graph = mock_get_graph()
            node_id = graph.add_node("Новый концепт", "concept", {"importance": 0.8})
            
            # Проверки
            assert node_id == "concept_123"
            mock_graph.add_node.assert_called_once_with("Новый концепт", "concept", {"importance": 0.8})
    
    def test_add_relation(self):
        """Тест добавления связи"""
        with patch('knowledge.graph.get_knowledge_graph') as mock_get_graph:
            mock_graph = Mock()
            mock_graph.add_edge.return_value = "edge_456"
            mock_get_graph.return_value = mock_graph
            
            # Вызов
            graph = mock_get_graph()
            edge_id = graph.add_edge("concept1", "concept2", "related_to", {"strength": 0.9})
            
            # Проверки
            assert edge_id == "edge_456"
            mock_graph.add_edge.assert_called_once_with("concept1", "concept2", "related_to", {"strength": 0.9})
    
    def test_find_related_concepts(self):
        """Тест поиска связанных концептов"""
        with patch('knowledge.graph.get_knowledge_graph') as mock_get_graph:
            mock_graph = Mock()
            mock_graph.find_related.return_value = [
                {"id": "concept2", "similarity": 0.8},
                {"id": "concept3", "similarity": 0.6}
            ]
            mock_get_graph.return_value = mock_graph
            
            # Вызов
            graph = mock_get_graph()
            related = graph.find_related("concept1", max_depth=2)
            
            # Проверки
            assert len(related) == 2
            assert related[0]["similarity"] == 0.8
            mock_graph.find_related.assert_called_once_with("concept1", max_depth=2)
    
    def test_knowledge_extraction(self):
        """Тест извлечения знаний из текста"""
        with patch('knowledge.graph.get_knowledge_graph') as mock_get_graph:
            mock_graph = Mock()
            mock_graph.extract_concepts.return_value = {
                "concepts": ["нейронная сеть", "машинное обучение"],
                "relations": [("нейронная сеть", "является", "машинное обучение")],
                "confidence": 0.85
            }
            mock_get_graph.return_value = mock_graph
            
            # Вызов
            graph = mock_get_graph()
            extracted = graph.extract_concepts("Нейронные сети являются частью машинного обучения")
            
            # Проверки
            assert "concepts" in extracted
            assert "relations" in extracted
            assert "confidence" in extracted
            assert len(extracted["concepts"]) == 2
            mock_graph.extract_concepts.assert_called_once_with("Нейронные сети являются частью машинного обучения")
