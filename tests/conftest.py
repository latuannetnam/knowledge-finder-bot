"""Pytest fixtures for knowledge-finder-bot tests."""

import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import yaml

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


@pytest.fixture
def acl_yaml_content():
    """Standard ACL config for bot integration tests."""
    return {
        "notebooks": [
            {
                "id": "*",
                "name": "All Notebooks",
                "allowed_groups": [
                    {
                        "group_id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
                        "display_name": "IT Admins",
                    },
                ],
            },
            {
                "id": "hr-notebook",
                "name": "HR Docs",
                "allowed_groups": [
                    {
                        "group_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "display_name": "HR Team",
                    },
                ],
            },
            {
                "id": "public-notebook",
                "name": "Public KB",
                "allowed_groups": ["*"],
            },
        ],
        "defaults": {
            "strict_mode": True,
            "no_access_message": "No access.",
        },
    }


@pytest.fixture
def acl_config_path(acl_yaml_content, tmp_path):
    """Write ACL config to a temp file and return the path."""
    config_file = tmp_path / "acl.yaml"
    config_file.write_text(yaml.dump(acl_yaml_content))
    return str(config_file)


@pytest.fixture
def mock_graph_client():
    """Mock GraphClient that returns configurable UserInfo."""
    from knowledge_finder_bot.auth.graph_client import UserInfo

    client = AsyncMock()
    client.get_user_with_groups = AsyncMock(
        return_value=UserInfo(
            aad_object_id="test-aad-id",
            display_name="Test User",
            email="test@company.com",
            groups=[
                {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "display_name": "HR Team"},
            ],
        )
    )
    client.close = AsyncMock()
    return client
