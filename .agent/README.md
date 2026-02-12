# AI Agent Project Guide

This file provides guidance for the AI Agent (Antigravity) when working with code in this repository.

## Modular Memory System

This project uses `.agent/memory/` for detailed context. Read [project_status.md](memory/project_status.md) for project overview, then drill into specific topics as needed.

## 📚 Documentation Maintenance

**Use the `/update-docs` workflow (if available) or manually keep documentation synchronized with code changes.**

### Documentation Update Rules (Reference)

This project generally follows these mappings for documentation updates:

| Change Type | Files to Update |
|-------------|-----------------|
| **New Feature/Module** | `README.md` (Features, Structure, Status), `docs/architecture.md`, `.agent/README.md` (components), `.agent/memory/project_structure.md`, `.agent/memory/project_status.md` |
| **Dependencies** | `README.md` (Prerequisites), `docs/setup.md`, `.agent/memory/dependencies.md` |
| **Environment Variables** | `README.md` (Env Vars), `docs/setup.md`, `.agent/README.md` (if critical), `.env.example` |
| **Code Patterns** | `.agent/rules/coding_patterns.md`, `docs/contributing.md` (if standard) |
| **Bug Fixes/Solutions** | `.agent/memory/debugging.md`, `README.md` (if known issue) |
| **Architecture Changes** | `README.md` (Architecture, Structure), `docs/architecture.md`, `.agent/README.md` (architecture) |
| **Development Tools** | `README.md` (Quick Start), `docs/setup.md`, `.agent/memory/project_status.md` |
| **Important Decisions** | `.agent/memory/decisions.md`, `docs/architecture.md` |
| **Test Results/Coverage** | `README.md` (badges, test results), `.agent/memory/project_status.md` |
| **Deployment Changes** | `README.md`, `docs/deployment.md` |

### Manual Updates

1. ✅ Identify what changed (feature, architecture, config, etc.)
2. ✅ Update relevant documentation files from table above
3. ✅ Update `.agent/memory/project_status.md` "Current Phase" if milestone reached
4. ✅ Verify code examples in docs still work
5. ✅ Update README.md if user-facing changes
6. ✅ Commit documentation updates WITH code changes

**Remember:** Documentation is code. Outdated docs are worse than no docs.

## Code Patterns & Standards

**Logging (Critical):**
- Use `structlog` exclusively.
- **Pattern:** `logger.info("event_name", key=value, status="active")`
- **NEVER** use f-strings in log messages: `logger.info(f"User {id}")` ❌
- See [coding_patterns.md](rules/coding_patterns.md) for details.

## Development Commands

```bash
# Setup
uv sync

# Run bot server
uv run python -m knowledge_finder_bot.main

# Run all tests
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_bot.py -v

# Run specific test
uv run pytest tests/test_bot.py::test_on_message_activity_echoes_message -v

# Start devtunnel (for Azure Bot Service integration)
.\run_devtunnel.ps1

# Test bot locally with Agent Playground
.\run_agentplayground.ps1

# Health check
curl http://localhost:3978/health

# Add dependency
uv add <package>

# Add dev dependency
uv add --group dev <package>
```

## Architecture

```
User (Teams/Telegram) → Azure Bot Service → Bot Backend (aiohttp:3978)
                                                  ↓
                                    ┌─────── Auth Middleware ────────┐
                                    │   (validate Bot Framework      │
                                    │    JWT token)                  │
                                    └────────────┬───────────────────┘
                                                 ↓
                                    ┌─────── Graph API Client ───────┐
                                    │   GET /users/{id}/memberOf     │
                                    │   Returns: AD group list       │
                                    └────────────┬───────────────────┘
                                                 ↓
                                    ┌─────── ACL Service ────────────┐
                                    │   Map groups → notebooks       │
                                    │   (from config/acl.yaml)       │
                                    └────────────┬───────────────────┘
                                                 ↓
                                    ┌─────── nlm-proxy Client ───────┐
                                    │   POST /v1/chat/completions    │
                                    │   stream=True, SSE chunks      │
                                    │   → StreamingResponse to user  │
                                    └────────────────────────────────┘
```

## Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Server** | `src/knowledge_finder_bot/main.py` | aiohttp app, `/api/messages`, `/health` |
| **Bot Handler** | `src/knowledge_finder_bot/bot/bot.py` | `create_agent_app()` - M365 Agents SDK |
| **Config** | `src/knowledge_finder_bot/config.py` | Pydantic settings from env vars |
| **Auth** | `src/knowledge_finder_bot/auth/` | Azure AD validation, Graph API |
| **ACL** | `src/knowledge_finder_bot/acl/` | Group → notebook mapping |
| **nlm-proxy** | `src/knowledge_finder_bot/nlm/` | OpenAI SDK client wrapper |
| **Channels** | `src/knowledge_finder_bot/channels/` | Teams/Telegram formatters |

## M365 Agents SDK Pattern

The bot follows the **official Microsoft Agents SDK pattern** from [github.com/microsoft/Agents](https://github.com/microsoft/Agents).

### Critical Requirements

**1. Environment Variables** - Use the SDK-specific format:
```bash
# Required by M365 Agents SDK (different from legacy Bot Framework!)
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=your-bot-app-id
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=your-bot-app-password
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=your-tenant-id
```

**2. Required Package** - Must include `microsoft-agents-authentication-msal`:
```toml
dependencies = [
    "microsoft-agents-hosting-core",
    "microsoft-agents-hosting-aiohttp",
    "microsoft-agents-activity",
    "microsoft-agents-authentication-msal",  # Critical for auth!
]
```

### Server Setup

```python
# main.py
from microsoft_agents.hosting.aiohttp import (
    start_agent_process,
    jwt_authorization_middleware,
)

app = Application(middlewares=[jwt_authorization_middleware])
app["agent_configuration"] = CONNECTION_MANAGER.get_default_connection_configuration()
app["agent_app"] = AGENT_APP
app["adapter"] = AGENT_APP.adapter  # Use adapter from agent app!

async def messages(request: Request) -> Response:
    return await start_agent_process(request, request.app["agent_app"], request.app["adapter"])
```

All I/O is async. Use `await` for M365 Agents SDK and Graph API calls.

## Testing

- **Unit tests:** Mock dependencies, test logic in isolation
- **Fixtures:** Defined in `tests/conftest.py` (settings, turn_context)
- **Async:** Use `@pytest.mark.asyncio` decorator
- **Coverage:** Run `uv run pytest --cov=knowledge_finder_bot tests/`

## Azure Configuration

Two Azure AD app registrations required (see [azure_config.md](memory/azure_config.md)):

1. **Bot Registration** (Bot Framework auth)
2. **Graph API Client** (read user groups with app-only permissions)

Environment variables in `.env` (never commit):

**M365 Agents SDK (required):**
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET`
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID`

**Legacy/Future features:**
- `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_APP_TENANT_ID`
- `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`

**ACL Configuration (optional):**
- `ACL_CONFIG_PATH` (default: `config/acl.yaml`)
- `GRAPH_CACHE_TTL` (default: `300` seconds)
- `GRAPH_CACHE_MAXSIZE` (default: `1000` users)

**Test Mode (Agent Playground testing):**
- `TEST_MODE` (default: `false`) - Enable dual-mode: fake AAD IDs → mock, real AAD IDs → Graph API
- `TEST_USER_GROUPS` (default: `""`) - Comma-separated group IDs for MockGraphClient

**nlm-proxy Configuration (optional):**
- `NLM_PROXY_URL` - nlm-proxy endpoint URL (e.g., `http://localhost:8000/v1`)
- `NLM_PROXY_API_KEY` - API key for nlm-proxy authentication
- `NLM_MODEL_NAME` (default: `knowledge-finder`)
- `NLM_TIMEOUT` (default: `60.0` seconds)
- `NLM_SESSION_TTL` (default: `86400` seconds / 24 hours)
- `NLM_SESSION_MAXSIZE` (default: `1000` concurrent sessions)

## Implementation Plans

Detailed step-by-step guides available in `docs/plans/`.

## Commands Cheatsheet

```bash
# Setup
uv sync

# Run bot
uv run python -m knowledge_finder_bot.main

# Run tests
uv run pytest tests/ -v
```
