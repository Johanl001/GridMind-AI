"""
Pytest configuration and fixtures for GridMind AI backend tests.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings, get_settings
import tempfile
import os
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    test_settings = Settings(
        DEBUG=True,
        DATABASE_URL="sqlite:///:memory:",
        GRIDMIND_API_KEY="test-secret-key",
        RANDOM_SEED=42
    )
    return test_settings


@pytest.fixture
def client(test_settings):
    """Create a test client with overridden settings."""
    # Override the get_settings dependency
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)