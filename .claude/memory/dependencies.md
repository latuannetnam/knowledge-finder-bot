# Dependencies

## Core Dependencies

```toml
[project]
requires-python = ">=3.11"

dependencies = [
    "microsoft-agents-hosting-core",     # M365 Agents SDK
    "microsoft-agents-hosting-aiohttp",
    "microsoft-agents-activity",
    "microsoft-agents-authentication-msal",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=23.0.0",
    "msal>=1.24.0",
    "httpx>=0.25.0",      # ✅ Graph API client (added for ACL)
    "pyyaml>=6.0",        # ✅ ACL YAML config (added for ACL)
    "cachetools>=5.3.0",  # ✅ User info caching (added for ACL)
]
```

## Dev Dependencies

```toml
[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
]
```

## Implementation Status

| Package | Purpose | Status |
|---------|---------|--------|
| `httpx>=0.25.0` | Graph API HTTP client | ✅ Implemented (ACL phase) |
| `pyyaml>=6.0` | ACL YAML config | ✅ Implemented (ACL phase) |
| `cachetools>=5.3.0` | User info caching | ✅ Implemented (ACL phase) |
| `openai>=1.0.0` | nlm-proxy client | ⏳ TODO (next phase) |
| `redis>=5.0.0` | Persistent caching | ⏳ Future (optional) |

## ACL Dependencies Details

**httpx** - Async HTTP client for Microsoft Graph API
- Used in: `auth/graph_client.py`
- Replaces: msgraph-sdk (lighter, more flexible)
- Features: Pagination, timeout handling, connection pooling

**pyyaml** - YAML parser for ACL configuration
- Used in: `acl/service.py`
- Config file: `config/acl.yaml`
- Hot-reload support via `reload_config()`

**cachetools** - In-memory caching
- Used in: `bot/bot.py`
- Cache type: TTLCache (5-min TTL, 1000 users)
- Reduces Graph API calls by ~95%

## Package Manager

**Always use `uv`**, not pip:

```bash
# Install all deps
uv sync

# Add new dependency
uv add <package>

# Add dev dependency
uv add --group dev <package>

# Run with deps
uv run python -m knowledge_finder_bot.main
uv run pytest tests/ -v
```
