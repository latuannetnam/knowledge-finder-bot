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

    # Azure Bot Registration - Legacy (optional, not used if CONNECTIONS__* vars are set)
    app_id: str = Field(
        "", alias="MICROSOFT_APP_ID",
        description="Azure Bot Registration app ID. Legacy field, optional when CONNECTIONS__* vars are set.",
    )
    app_password: str = Field(
        "", alias="MICROSOFT_APP_PASSWORD",
        description="Azure Bot Registration app password. Legacy field, optional when CONNECTIONS__* vars are set.",
    )

    # Tenant ID (shared by Bot and Graph API)
    app_tenant_id: str = Field(
        ..., alias="MICROSOFT_APP_TENANT_ID",
        description="Azure AD tenant ID. Required for both Bot authentication and Graph API client.",
    )

    # Graph API Client
    graph_client_id: str = Field(
        ..., alias="GRAPH_CLIENT_ID",
        description="Client ID for the Graph API app registration, used to look up user info and group memberships.",
    )
    graph_client_secret: str = Field(
        ..., alias="GRAPH_CLIENT_SECRET",
        description="Client secret for the Graph API app registration.",
    )

    # ACL
    acl_config_path: str = Field(
        "config/acl.yaml", alias="ACL_CONFIG_PATH",
        description="Path to the ACL YAML config that maps Azure AD groups to allowed NotebookLM notebooks.",
    )

    # Graph API cache
    graph_cache_ttl: int = Field(
        300, alias="GRAPH_CACHE_TTL",
        description="TTL in seconds for caching Graph API user/group lookups. Reduces API calls for repeated requests.",
    )
    graph_cache_maxsize: int = Field(
        1000, alias="GRAPH_CACHE_MAXSIZE",
        description="Max number of cached Graph API user entries. LRU eviction when exceeded.",
    )

    # Test Mode (for Agent Playground testing)
    test_mode: bool = Field(
        False, alias="TEST_MODE",
        description="Enable dual-mode auth: real Graph API for valid AAD IDs, mock client for Agent Playground fake IDs.",
    )
    test_user_groups: str = Field(
        "", alias="TEST_USER_GROUPS",
        description="Comma-separated Azure AD group IDs assigned to mock users in test mode.",
    )

    # nlm-proxy (empty defaults = optional, graceful fallback to echo)
    nlm_proxy_url: str = Field(
        "", alias="NLM_PROXY_URL",
        description="Base URL of the nlm-proxy OpenAI-compatible API (e.g. http://host:8000/v1). Empty = echo mode.",
    )
    nlm_proxy_api_key: str = Field(
        "", alias="NLM_PROXY_API_KEY",
        description="API key for authenticating with nlm-proxy. Empty = echo mode.",
    )
    nlm_model_name: str = Field(
        "knowledge-finder", alias="NLM_MODEL_NAME",
        description="Model name sent to nlm-proxy, maps to a NotebookLM notebook configuration.",
    )
    nlm_timeout: float = Field(
        60.0, alias="NLM_TIMEOUT",
        description="HTTP request timeout in seconds for nlm-proxy calls.",
    )
    nlm_memory_ttl: int = Field(
        3600, alias="NLM_MEMORY_TTL",
        description="TTL in seconds for conversation memory sessions. Sessions expire after this period of inactivity.",
    )
    nlm_memory_maxsize: int = Field(
        1000, alias="NLM_MEMORY_MAXSIZE",
        description="Max number of concurrent conversation sessions in memory. LRU eviction when exceeded.",
    )
    nlm_memory_max_messages: int = Field(
        10, alias="NLM_MEMORY_MAX_MESSAGES",
        description="Max messages kept per session (sliding window). 10 = 5 Q&A exchanges. Set to 0 for unlimited.",
    )
    nlm_enable_rewrite: bool = Field(
        True, alias="NLM_ENABLE_REWRITE",
        description="Auto-rewrite follow-up questions as standalone using conversation history context.",
    )
    nlm_enable_followup: bool = Field(
        True, alias="NLM_ENABLE_FOLLOWUP",
        description="Generate follow-up question suggestions after each bot response.",
    )

    # Server
    host: str = Field(
        "0.0.0.0", alias="HOST",
        description="Host address to bind the aiohttp server to.",
    )
    port: int = Field(
        3978, alias="PORT",
        description="Port number for the aiohttp server. Azure Bot Service expects 3978 by default.",
    )

    # Logging
    log_level: str = Field(
        "INFO", alias="LOG_LEVEL",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL.",
    )
    log_file: str = Field(
        "", alias="LOG_FILE",
        description="Path to log file for file-based logging with rotation. Empty = console only.",
    )
    log_file_max_bytes: int = Field(
        10_485_760, alias="LOG_FILE_MAX_BYTES",
        description="Max size in bytes per log file before rotation. Default: 10 MB.",
    )
    log_file_backup_count: int = Field(
        5, alias="LOG_FILE_BACKUP_COUNT",
        description="Number of rotated backup log files to keep.",
    )


def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()
