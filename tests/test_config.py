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


def test_settings_has_acl_defaults(settings: Settings):
    """Test that ACL settings have correct defaults."""
    assert settings.acl_config_path == "config/acl.yaml"
    assert settings.graph_cache_ttl == 300
    assert settings.graph_cache_maxsize == 1000


def test_settings_has_logging_file_defaults(settings: Settings):
    """Test that file logging settings have correct defaults."""
    assert settings.log_file == ""
    assert settings.log_file_max_bytes == 10_485_760  # 10 MB
    assert settings.log_file_backup_count == 5
