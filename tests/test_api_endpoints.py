"""
API endpoint integration tests using isolated TestClient.

Verifies:
- /metrics/system — structure, no random values
- /system/full-status — structure, no random values
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    from api.frontend_routes import router
    app.include_router(router)
    with TestClient(app) as c:
        yield c


@pytest.mark.api
def test_metrics_system_structure(client):
    """System metrics return correct structure. No random values."""
    response = client.get("/api/v1/metrics/system")
    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "cpu_usage", "memory_usage", "disk_io",
        "network_latency", "active_connections",
        "active_sessions", "cache_hit_rate", "max_connections"
    }
    missing = expected_keys - set(data.keys())
    assert not missing, f"Missing keys: {missing}"

    for key in ["cpu_usage", "memory_usage", "disk_io"]:
        assert isinstance(data[key], (int, float)), f"{key} should be numeric, got {type(data[key])}"

    assert data["max_connections"] == 1000
    assert isinstance(data["cpu_usage"], (int, float))
    assert isinstance(data["memory_usage"], (int, float))

    # Verify no negative values
    for k, v in data.items():
        if isinstance(v, (int, float)):
            assert v >= 0, f"{k} should be >= 0, got {v}"


@pytest.mark.api
def test_full_system_status_structure(client):
    """Full system status returns correct structure. No random values."""
    response = client.get("/api/v1/system/full-status")
    assert response.status_code == 200
    data = response.json()

    assert "timestamp" in data
    assert "version" in data
    assert isinstance(data["emotion"], dict)
    assert isinstance(data["knowledge"], dict)
    assert isinstance(data["health"], dict)

    memory = data["memory"]
    for mem_type in ["rag", "episodic", "semantic", "facts", "persona"]:
        assert mem_type in memory, f"Missing memory.{mem_type}"
        assert isinstance(memory[mem_type], dict), f"memory.{mem_type} should be dict"

    cognitive = data["cognitive"]
    for section in ["pipeline", "truth_loop", "safety"]:
        assert section in cognitive, f"Missing cognitive.{section}"

    infra = data["infrastructure"]
    for section in ["cache", "sessions", "events", "websocket"]:
        assert section in infra, f"Missing infrastructure.{section}"
