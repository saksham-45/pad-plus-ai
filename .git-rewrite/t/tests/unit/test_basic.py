"""
Простые unit тесты для проверки структуры
"""

import pytest
from unittest.mock import Mock, AsyncMock, mock_open, patch

@pytest.mark.unit
def test_mock_functionality():
    """Тест работы моков"""
    mock_obj = Mock()
    mock_obj.return_value = "test_result"
    
    result = mock_obj()
    assert result == "test_result"
    mock_obj.assert_called_once()

@pytest.mark.unit
def test_patch_functionality():
    """Тест работы патчей"""
    with patch('builtins.open', mock_open(read_data="test_content")) as mock_opened:
        with open("test_file.txt") as f:
            content = f.read()
        
        assert content == "test_content"
        mock_opened.assert_called_once_with("test_file.txt")

@pytest.mark.unit
def test_async_mock():
    """Тест работы асинхронных моков"""
    import asyncio
    
    async_mock = AsyncMock()
    async_mock.return_value = {"status": "ok"}
    
    async def test_coroutine():
        result = await async_mock()
        return result
    
    result = asyncio.run(test_coroutine())
    assert result["status"] == "ok"

@pytest.mark.unit
class TestBasicFunctionality:
    """Тест базовой функциональности"""
    
    def test_list_operations(self):
        """Тест операций со списками"""
        data = [1, 2, 3]
        assert len(data) == 3
        assert 2 in data
        
        data.append(4)
        assert len(data) == 4
        assert 4 in data
    
    def test_dict_operations(self):
        """Тест операций со словарями"""
        data = {"key1": "value1", "key2": "value2"}
        assert "key1" in data
        assert data["key1"] == "value1"
        
        data["key3"] = "value3"
        assert len(data) == 3
        assert data["key3"] == "value3"
    
    def test_string_operations(self):
        """Тест операций со строками"""
        text = "Hello, World!"
        assert "Hello" in text
        assert text.startswith("Hello")
        assert text.endswith("!")
        
        upper_text = text.upper()
        assert upper_text == "HELLO, WORLD!"
        
        words = text.split(", ")
        assert len(words) == 2
        assert words[0] == "Hello"
        assert words[1] == "World!"
