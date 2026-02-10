# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Modular Memory System

This project uses `.claude/memory/` for detailed context. Read [MEMORY.md](.claude/memory/MEMORY.md) for project overview, then drill into specific topics as needed.

## 📚 Documentation Maintenance

**CRITICAL: Always update Just-in-Time documentation after completing tasks.**

### When to Update Documentation

Update docs **immediately after**:
- ✅ Adding new features or modules
- ✅ Refactoring code structure (moving files, renaming modules)
- ✅ Changing architecture or data flow
- ✅ Adding/removing/updating dependencies
- ✅ Modifying environment variables or configuration
- ✅ Discovering bugs or creating solutions
- ✅ Establishing new coding patterns
- ✅ Changing development workflow or tooling

### What to Update

| Change Type | Files to Update |
|-------------|-----------------|
| **New Feature/Module** | `docs/architecture.md`, `CLAUDE.md` (components), `.claude/memory/project-structure.md` |
| **Dependencies** | `.claude/memory/dependencies.md`, `docs/setup.md` (if prerequisites change) |
| **Environment Variables** | `docs/setup.md`, `CLAUDE.md` (if critical), `.env.example` |
| **Code Patterns** | `.claude/memory/patterns.md` |
| **Bug Fixes/Solutions** | `.claude/memory/debugging.md` |
| **Architecture Changes** | `docs/architecture.md`, `CLAUDE.md` (architecture section) |
| **Development Tools** | `docs/setup.md`, `.claude/memory/MEMORY.md` (quick reference) |
| **Important Decisions** | `.claude/memory/decisions.md` |

### Documentation Update Checklist

Before marking a task complete:
1. ✅ Identify what changed (feature, architecture, config, etc.)
2. ✅ Update relevant documentation files from table above
3. ✅ Update `.claude/memory/MEMORY.md` "Current Phase" if milestone reached
4. ✅ Verify code examples in docs still work
5. ✅ Update README.md if user-facing changes
6. ✅ Commit documentation updates WITH code changes

**Remember:** Documentation is code. Outdated docs are worse than no docs.

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

Detailed step-by-step guides:
- **Migration:** `docs/plans/2025-02-09-m365-agents-migration-plan.md` ✅ Completed (commit dbeed4c)
- **ACL Mechanism:** `docs/plans/2025-02-10-acl-mechanism.md` ✅ Completed (commits 5206eed → cf59c42)
- **nlm-proxy Integration:** `docs/plans/2025-02-10-nlm-proxy-integration.md` ✅ Completed (72/72 tests passing)
- **Basic (echo bot):** `docs/plans/2025-02-09-notebooklm-chatbot-basic.md`
- **Full design:** `docs/docs\plans\notebooklm-chatbot-design-v2-fixed.md`

## Implementation Status

**✅ M365 Agents SDK Migration Complete** (commit: `dbeed4c`)
- Migrated from Bot Framework SDK to M365 Agents SDK v0.7.0
- All tests passing (4/4)
- Echo bot functional with decorator-based handlers

**✅ ACL Mechanism Complete** (commits: `5206eed` → `cf59c42`)
- Graph API client with app-only authentication (8/8 tests)
- ACL service with YAML-based access control (14/14 tests)
- Pydantic models with GUID validation (11/11 tests)
- Bot handler with ACL enforcement and graceful fallback (10/10 tests)
- **Dual-mode routing**: Fake AAD IDs (Agent Playground) → MockGraphClient, real AAD IDs → Graph API
- MockGraphClient for Agent Playground testing without Azure AD

**✅ nlm-proxy Integration Complete** (branch: `feature/nlm-proxy-integration`)
- NLMClient with AsyncOpenAI SDK (8/8 tests)
  - Streaming responses with SSE chunk buffering
  - Non-streaming fallback
  - Conversation ID extraction from `system_fingerprint` (format: `conv_{id}`)
  - `extra_body` for `metadata.allowed_notebooks` per-request ACL
- SessionStore for multi-turn conversations (6/6 tests)
  - TTLCache with 24-hour expiry
  - Maps AAD Object ID → conversation ID
- Response formatter with source attribution (5/5 tests)
- Bot integration (7/7 tests)
  - Typing indicator before query
  - Multi-turn conversation support
  - Graceful error handling
  - Fallback to echo mode when nlm-proxy not configured
- **Total: 72/72 tests passing, 77% code coverage**

**✅ End-to-End Streaming Complete** (branch: `feature/nlm-proxy-integration`)
- NLMClient.query_stream() async generator yields chunks in real-time (9/9 tests)
- StreamingResponse pipes tokens directly to Teams/DirectLine (9/9 tests)
- Informative status update with notebook name ("Searching HR Docs...")
- Reasoning + separator + answer content streamed to user
- Source attribution appended at stream end
- **Total: 87/87 tests passing**

## Test Mode for Agent Playground

The bot supports **dual-mode routing** for testing ACL logic in Agent Playground without Azure AD:

**How it works:**
1. Enable `TEST_MODE=true` in `.env`
2. Set `TEST_USER_GROUPS` to simulate AD group memberships (comma-separated GUIDs)
3. Bot automatically detects AAD ID prefix:
   - `00000000-0000-0000-0000-*` (Agent Playground) → MockGraphClient
   - Real AAD IDs (Teams/Telegram) → Real Graph API
4. Both modes coexist — per-request routing based on AAD ID pattern

**Example configuration:**
```bash
# .env
TEST_MODE=true
TEST_USER_GROUPS=22222222-2222-2222-2222-222222222222,33333333-3333-3333-3333-333333333333
```

**Test groups** (defined in `config/acl.yaml`):
- `11111111-1111-1111-1111-111111111111` - Test Admin (all notebooks)
- `22222222-2222-2222-2222-222222222222` - Test HR (hr-notebook + public)
- `33333333-3333-3333-3333-333333333333` - Test Engineering (engineering-notebook + public)

See `.env.example` for complete TEST_MODE examples.
