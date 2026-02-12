"""Test that legacy auth variables are optional."""

import os
import pytest
from unittest.mock import patch

from knowledge_finder_bot.config import Settings


def test_settings_without_legacy_app_id_and_password():
    """Test that Settings can be created without MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD."""
    env_vars = {
        # Only TENANT_ID is required for Graph API
        "MICROSOFT_APP_TENANT_ID": "test-tenant-id",
        "GRAPH_CLIENT_ID": "test-graph-client-id",
        "GRAPH_CLIENT_SECRET": "test-graph-client-secret",
        "HOST": "127.0.0.1",
        "PORT": "3978",
        "LOG_LEVEL": "DEBUG",
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        # Create Settings without loading from .env file
        settings = Settings(_env_file=None)
        
        # These should have empty defaults
        assert settings.app_id == ""
        assert settings.app_password == ""
        
        # This should be set
        assert settings.app_tenant_id == "test-tenant-id"
        assert settings.graph_client_id == "test-graph-client-id"
        assert settings.graph_client_secret == "test-graph-client-secret"


def test_settings_with_legacy_variables_still_works():
    """Test that Settings still works when legacy variables are provided."""
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
    
    with patch.dict(os.environ, env_vars, clear=True):
        # Create Settings without loading from .env file
        settings = Settings(_env_file=None)
        
        # All should be set
        assert settings.app_id == "test-app-id"
        assert settings.app_password == "test-app-password"
        assert settings.app_tenant_id == "test-tenant-id"
