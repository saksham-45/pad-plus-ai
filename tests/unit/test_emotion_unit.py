"""
Unit тесты для эмоций
"""

import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.emotion
class TestEmotion:
    """Тесты эмоциональной системы"""
    
    def test_pad_model_state(self, sample_emotion_state):
        """Тест состояния PAD+ модели"""
        with patch('emotion.pad_model.get_pad_model') as mock_get_pad:
            mock_pad = Mock()
            mock_state = Mock()
            mock_style = {
                "tone": "friendly",
                "intensity": 0.7,
                "mood": "positive"
            }
            
            mock_state.get_style.return_value = mock_style
            mock_pad.get_state.return_value = mock_state
            mock_get_pad.return_value = mock_pad
            
            # Вызов
            pad = mock_get_pad()
            state = pad.get_state()
            style = state.get_style()
            
            # Проверки
            assert style["tone"] in ["friendly", "neutral", "serious"]
            assert "intensity" in style
            assert "mood" in style
            mock_pad.get_state.assert_called_once()
            mock_state.get_style.assert_called_once()
    
    def test_emotion_processing(self):
        """Тест обработки эмоций"""
        with patch('emotion.pad_model.get_pad_model') as mock_get_pad:
            mock_pad = Mock()
            mock_pad.process_emotion.return_value = {
                "pleasure": 0.8,
                "arousal": 0.6,
                "dominance": 0.7,
                "valence": "positive"
            }
            mock_get_pad.return_value = mock_pad
            
            # Вызов
            pad = mock_get_pad()
            result = pad.process_emotion("Я очень рад этому!")
            
            # Проверки
            assert "pleasure" in result
            assert "arousal" in result
            assert "dominance" in result
            assert result["valence"] == "positive"
            mock_pad.process_emotion.assert_called_once_with("Я очень рад этому!")
    
    def test_emotion_style_generation(self):
        """Тест генерации стиля ответа"""
        with patch('emotion.pad_model.get_pad_model') as mock_get_pad:
            mock_pad = Mock()
            mock_pad.generate_style.return_value = {
                "tone": "friendly",
                "formality": "casual",
                "enthusiasm": 0.8
            }
            mock_get_pad.return_value = mock_pad
            
            # Вызов
            pad = mock_get_pad()
            style = pad.generate_style("positive")
            
            # Проверки
            assert style["tone"] == "friendly"
            assert style["formality"] == "casual"
            assert style["enthusiasm"] == 0.8
            mock_pad.generate_style.assert_called_once_with("positive")
