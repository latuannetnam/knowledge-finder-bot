# Dependencies

## Core Dependencies

```toml
[project]
requires-python = ">=3.11"

dependencies = [
    "botbuilder-core>=4.14.0",
    "botbuilder-integration-aiohttp>=4.14.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=23.0.0",
    "msal>=1.24.0",
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

## Future Dependencies (Advanced Phase)

| Package | Purpose | When to Add |
|---------|---------|-------------|
| `openai>=1.0.0` | nlm-proxy client | Phase 4 |
| `msgraph-sdk>=1.0.0` | Graph API | Phase 2 |
| `redis>=5.0.0` | ACL caching | Phase 3 |
| `pyyaml>=6.0.0` | ACL config | Phase 3 |

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
