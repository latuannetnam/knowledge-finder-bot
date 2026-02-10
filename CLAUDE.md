# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Modular Memory System

This project uses `.claude/memory/` for detailed context. Read [MEMORY.md](.claude/memory/MEMORY.md) for project overview, then drill into specific topics as needed.

## Code Patterns & Standards

**Logging (Critical):**
- Use `structlog` exclusively.
- **Pattern:** `logger.info("event_name", key=value, status="active")`
- **NEVER** use f-strings in log messages: `logger.info(f"User {id}")` ❌
- See [patterns.md](.claude/memory/patterns.md) for details.

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

# Start tunnel for Teams testing
nport 3978 -s knowledge-finder-bot

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
                                    │   model: knowledge-finder      │
                                    │   metadata: allowed_notebooks  │
                                    └────────────┬───────────────────┘
                                                 ↓
                                    ┌─── Response Formatter ─────────┐
                                    │   Extract notebook from        │
                                    │   reasoning_content            │
                                    │   Add source attribution       │
                                    └────────────┬───────────────────┘
                                                 ↓
                                         Send to User
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

### Architecture Pattern

```python
# Load SDK configuration from environment (critical!)
from microsoft_agents.activity import load_configuration_from_env
agents_sdk_config = load_configuration_from_env(environ)

# Create core components
from microsoft_agents.authentication.msal import MsalConnectionManager
STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

# Create agent application
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config
)

# Register handlers with decorators
@AGENT_APP.message(re.compile(r".*"))
async def on_message(context: TurnContext, state: TurnState):
    await context.send_activity(f"Echo: {context.activity.text}")

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):
    await context.send_activity("Welcome!")
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

Two Azure AD app registrations required (see [azure-config.md](.claude/memory/azure-config.md)):

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

## Implementation Plans

Detailed step-by-step guides:
- **Migration:** `docs/plans/2025-02-09-m365-agents-migration-plan.md` ✅ Completed (commit dbeed4c)
- **Basic (echo bot):** `docs/plans/2025-02-09-notebooklm-chatbot-basic.md`
- **Advanced (full features):** `docs/plans/2025-02-09-notebooklm-chatbot-advanced.md`
- **Full design:** `docs/plans/notebooklm-chatbot-design.md`

## Migration Status

**✅ M365 Agents SDK Migration Complete** (commit: `dbeed4c`)
- Migrated from Bot Framework SDK to M365 Agents SDK v0.7.0
- All tests passing (4/4)
- Echo bot functional with decorator-based handlers
