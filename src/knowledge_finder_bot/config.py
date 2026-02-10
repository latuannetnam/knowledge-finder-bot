"""Application configuration using Pydantic settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure Bot Registration
    app_id: str = Field(..., alias="MICROSOFT_APP_ID")
    app_password: str = Field(..., alias="MICROSOFT_APP_PASSWORD")
    app_tenant_id: str = Field(..., alias="MICROSOFT_APP_TENANT_ID")

    # Graph API Client
    graph_client_id: str = Field(..., alias="GRAPH_CLIENT_ID")
    graph_client_secret: str = Field(..., alias="GRAPH_CLIENT_SECRET")

    # ACL
    acl_config_path: str = Field("config/acl.yaml", alias="ACL_CONFIG_PATH")

    # Graph API cache
    graph_cache_ttl: int = Field(300, alias="GRAPH_CACHE_TTL")
    graph_cache_maxsize: int = Field(1000, alias="GRAPH_CACHE_MAXSIZE")

    # Test Mode (for Agent Playground testing)
    test_mode: bool = Field(False, alias="TEST_MODE")
    test_user_groups: str = Field("", alias="TEST_USER_GROUPS")  # Comma-separated group IDs

    # Server
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(3978, alias="PORT")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")


def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()
