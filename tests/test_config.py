"""Tests for configuration module."""

import pytest

from knowledge_finder_bot.config import Settings


def test_settings_loads_from_env(settings: Settings):
    """Test that settings loads values from environment variables."""
    assert settings.app_id == "test-app-id"
    assert settings.app_password == "test-app-password"
    assert settings.app_tenant_id == "test-tenant-id"


def test_settings_has_defaults(settings: Settings):
    """Test that settings has correct default values."""
    assert settings.host == "127.0.0.1"
    assert settings.port == 3978
    assert settings.log_level == "DEBUG"
