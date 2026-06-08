from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.knowledge_graph import KnowledgeGraphPhase


async def test_knowledge_graph_with_concepts():
    mock_concept = MagicMock()
    mock_concept.name = "С„РёР·РёРєР°"

    with patch("knowledge.graph.get_knowledge_graph") as mock_get:
        mock_graph = MagicMock()
        mock_graph.find_concepts.return_value = [mock_concept]
        mock_get.return_value = mock_graph

        phase = KnowledgeGraphPhase()
        ctx = PipelineContext(user_message="С„РёР·РёРєР° С‡Р°СЃС‚РёС†")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["concepts"] == ["С„РёР·РёРєР°"]
    assert result.data["confidence"] == 0.7


async def test_knowledge_graph_empty():
    with patch("knowledge.graph.get_knowledge_graph") as mock_get:
        mock_graph = MagicMock()
        mock_graph.find_concepts.return_value = []
        mock_get.return_value = mock_graph

        phase = KnowledgeGraphPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["concepts"] == []
    assert result.data["confidence"] == 0.0


async def test_knowledge_graph_fallback():
    with patch("knowledge.graph.get_knowledge_graph") as mock_get:
        mock_get.side_effect = Exception("graph unavailable")

        phase = KnowledgeGraphPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["concepts"] == []
