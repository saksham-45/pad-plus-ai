from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.save_episode import SaveEpisodePhase


async def test_save_episode_success():
    mock_episode = MagicMock()
    mock_episode.id = "ep_123"

    with patch("memory.episodic.get_episodic_memory") as mock_get:
        mock_mem = MagicMock()
        mock_mem.add_episode.return_value = mock_episode
        mock_get.return_value = mock_mem

        phase = SaveEpisodePhase()
        ctx = PipelineContext(
            user_message="РџСЂРёРІРµС‚",
            context={
                "response": "РџСЂРёРІРµС‚!",
                "intent": "chat_general",
                "rag_used": True,
                "truth_confidence": 0.8,
                "emotion_state": {"СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ": 0.7},
                "user_id": "user_1",
            },
        )
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["episode_id"] == "ep_123"


async def test_save_episode_fallback():
    with patch("memory.episodic.get_episodic_memory") as mock_get:
        mock_get.side_effect = Exception("episodic unavailable")

        phase = SaveEpisodePhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚", context={})
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["episode_id"] is None
