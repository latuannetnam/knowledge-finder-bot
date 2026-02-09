"""Pytest fixtures for nlm-chatbot tests."""

import os
from unittest.mock import patch

import pytest

from knowledge_finder_bot.config import Settings


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "MICROSOFT_APP_ID": "test-app-id",
        "MICROSOFT_APP_PASSWORD": "test-app-password",
        "MICROSOFT_APP_TENANT_ID": "test-tenant-id",
        "GRAPH_CLIENT_ID": "test-graph-client-id",
        "GRAPH_CLIENT_SECRET": "test-graph-client-secret",
        "HOST": "127.0.0.1",
        "PORT": "3978",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def settings(mock_env_vars) -> Settings:
    """Create Settings instance with mocked environment."""
    return Settings()
