"""
Health check endpoint tests.
"""
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint():
    """Test that the health endpoint returns 200 OK."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_endpoint():
    """Test that the root endpoint returns API information."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "GridMind AI" in data["message"]
    assert "docs" in data
    assert "health" in data