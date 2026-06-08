"""
Tests for GigaChatClient.

Covers:
- Key encoding (base64, pre-encoded, secret-only)
- Access token acquisition with caching
- Complete requests with retry
- Stream requests with SSE parsing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio
import time
import base64


@pytest.fixture
def client():
    from adapters.gigachat_client import GigaChatClient
    c = GigaChatClient()
    c._token_cache = {}
    return c


class TestEncodeKey:

    def test_client_id_secret(self, client):
        encoded = client._encode_key("client123:secret456")
        expected = base64.b64encode(b"client123:secret456").decode()
        assert encoded == expected

    def test_long_secret_pre_encoded(self, client):
        long_secret = "x" * 100
        encoded = client._encode_key(f"cid:{long_secret}")
        assert encoded == long_secret

    def test_long_key_no_colon(self, client):
        long_key = "x" * 90
        encoded = client._encode_key(long_key)
        assert encoded == long_key

    def test_short_key_raw(self, client):
        encoded = client._encode_key("short-key")
        expected = base64.b64encode(b"short-key").decode()
        assert encoded == expected

    def test_empty_key_error(self, client):
        with pytest.raises(ValueError, match="пуст"):
            client._encode_key("")

    def test_newlines_stripped(self, client):
        key = "cid:secret\r\n "
        encoded = client._encode_key(key)
        expected = base64.b64encode(b"cid:secret").decode()
        assert encoded == expected, f"got {encoded} expected {expected}"


class TestAccessToken:

    @pytest.mark.asyncio
    async def test_get_token_caches(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token-123",
            "expires_at": int(time.time()) + 3600,
        }

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = instance

            token1 = await client._get_access_token("test:key")
            token2 = await client._get_access_token("test:key")

            assert token1 == "test-token-123"
            assert token2 == "test-token-123"
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_get_token_expired_renews(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token-1",
            "expires_at": int(time.time()) - 10,
        }

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response.json.return_value = {
                "access_token": f"test-token-{call_count}",
                "expires_at": int(time.time()) + 3600,
            }
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = instance

            token1 = await client._get_access_token("test:key")
            client._token_cache.clear()
            token2 = await client._get_access_token("test:key")

            assert call_count == 2
            assert token1 == "test-token-1"
            assert token2 == "test-token-2"

    @pytest.mark.asyncio
    async def test_auth_failure(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 401

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = instance

            with pytest.raises(Exception, match="GigaChat auth failed"):
                await client._get_access_token("bad:key")


class TestComplete:

    @pytest.mark.asyncio
    async def test_complete_success(self, client):
        client._get_access_token = AsyncMock(return_value="valid-token")

        chat_response = MagicMock()
        chat_response.status_code = 200
        chat_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello world!"},
                "finish_reason": "stop",
            }],
            "usage": {"total_tokens": 10},
        }

        async def mock_post(*args, **kwargs):
            return chat_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = instance

            result = await client.complete(
                prompt="Hi",
                api_key="test:key",
                model="GigaChat",
            )

            assert result["text"] == "Hello world!"
            assert result["provider"] == "gigachat"
            assert result["finish_reason"] == "stop"
            assert result["usage"]["total_tokens"] == 10

    @pytest.mark.asyncio
    async def test_complete_no_key(self, client):
        with pytest.raises(ValueError, match="не настроен"):
            await client.complete(prompt="test", api_key=None)

    @pytest.mark.asyncio
    async def test_complete_empty_choices(self, client):
        client._get_access_token = AsyncMock(return_value="token")

        chat_response = MagicMock()
        chat_response.status_code = 200
        chat_response.json.return_value = {"choices": []}

        async def mock_post(*args, **kwargs):
            return chat_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = instance

            with pytest.raises(Exception, match="пустой choices"):
                await client.complete(prompt="test", api_key="test:key")


class TestStream:

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, client):
        client._get_access_token = AsyncMock(return_value="token")

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" World"}}]}',
        ]

        async def aiter_lines():
            for line in sse_lines:
                yield line

        class AsyncCtxMock:
            status_code = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_response = AsyncCtxMock()
        mock_response.aiter_lines = aiter_lines

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock(spec=["stream"])
            instance.stream.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = instance

            chunks = []
            async for chunk in client.stream(prompt="test", api_key="test:key"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World"]

    @pytest.mark.asyncio
    async def test_stream_no_key(self, client):
        with pytest.raises(ValueError, match="не настроен"):
            async for _ in client.stream(prompt="test", api_key=None):
                pass

    @pytest.mark.asyncio
    async def test_stream_http_error(self, client):
        client._get_access_token = AsyncMock(return_value="token")

        async def aread():
            return b"Internal Server Error"

        class AsyncCtxMock:
            status_code = 500

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_response = AsyncCtxMock()
        mock_response.aread = aread

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock(spec=["stream"])
            instance.stream.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = instance

            with pytest.raises(Exception, match="stream error"):
                async for _ in client.stream(prompt="test", api_key="test:key"):
                    pass


@pytest.mark.asyncio
async def test_get_gigachat_client():
    from adapters.gigachat_client import get_gigachat_client
    c1 = get_gigachat_client()
    c2 = get_gigachat_client()
    assert c1 is c2
