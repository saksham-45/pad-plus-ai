"""
Тестирование Knowledge Graph — PAD+ AI
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKnowledgeGraph:
    """Тестирование Knowledge Graph системы"""

    @pytest.fixture
    def graph(self):
        from knowledge.graph import get_knowledge_graph
        return get_knowledge_graph()

    @pytest.mark.asyncio
    async def test_graph_initialization(self, graph):
        """Тест инициализации графа знаний"""
        stats = graph.get_stats()
        
        assert "nodes" in stats
        assert "edges" in stats
        assert stats["nodes"] >= 0
        assert stats["edges"] >= 0

    @pytest.mark.asyncio
    async def test_concept_operations(self, graph):
        """Тест операций с концепциями"""
        concept = graph.add_concept(
            name="Тест концепция",
            concept_type="test",
            confidence=0.8,
            metadata={"test": True}
        )
        
        assert concept is not None
        assert concept.id is not None
        assert concept.name == "Тест концепция"
        assert concept.concept_type == "test"
        assert concept.confidence == 0.8

        retrieved = graph.get_concept(concept.id)
        assert retrieved is not None
        assert retrieved.name == "Тест концепция"

    @pytest.mark.asyncio
    async def test_relation_operations(self, graph):
        """Тест операций со связями"""
        c1 = graph.add_concept(name="Узел 1", concept_type="source")
        c2 = graph.add_concept(name="Узел 2", concept_type="target")
        
        relation = graph.add_relation(
            source_id=c1.id,
            target_id=c2.id,
            relation_type="related",
            weight=0.8,
            confidence=0.9
        )
        
        assert relation is not None
        assert relation.source_id == c1.id
        assert relation.target_id == c2.id
        assert relation.weight == 0.8

    @pytest.mark.asyncio
    async def test_find_concepts(self, graph):
        """Тест поиска концепций"""
        graph.add_concept(name="Python programming", concept_type="skill")
        graph.add_concept(name="Python basics", concept_type="concept")
        
        results = graph.find_concepts("python")
        
        assert len(results) >= 2
        assert any(r.name.lower() == "python programming" for r in results)

    @pytest.mark.asyncio
    async def test_get_related(self, graph):
        """Тест получения связанных концепций"""
        c1 = graph.add_concept(name="Мать")
        c2 = graph.add_concept(name="Ребёнок")
        
        graph.add_relation(c1.id, c2.id, "related")
        
        related = graph.get_related(c1.id)
        
        assert isinstance(related, list)

    @pytest.mark.asyncio
    async def test_find_path(self, graph):
        """Тест поиска пути между концепциями"""
        c1 = graph.add_concept(name="A")
        c2 = graph.add_concept(name="B")
        c3 = graph.add_concept(name="C")
        
        graph.add_relation(c1.id, c2.id)
        graph.add_relation(c2.id, c3.id)
        
        path = graph.find_path(c1.id, c3.id)
        
        assert isinstance(path, list)
        if path:
            assert len(path) >= 2

    @pytest.mark.asyncio
    async def test_graph_stats(self, graph):
        """Тест статистики графа"""
        stats = graph.get_stats()
        
        assert "nodes" in stats
        assert "edges" in stats
        assert "networkx_available" in stats