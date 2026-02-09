# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Modular Memory System

This project uses `.claude/memory/` for detailed context. Read [MEMORY.md](.claude/memory/MEMORY.md) for project overview, then drill into specific topics as needed.

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
| **Bot Handler** | `src/knowledge_finder_bot/bot/bot.py` | `NotebookLMBot(ActivityHandler)` |
| **Config** | `src/knowledge_finder_bot/config.py` | Pydantic settings from env vars |
| **Auth** | `src/knowledge_finder_bot/auth/` | Azure AD validation, Graph API |
| **ACL** | `src/knowledge_finder_bot/acl/` | Group → notebook mapping |
| **nlm-proxy** | `src/knowledge_finder_bot/nlm/` | OpenAI SDK client wrapper |
| **Channels** | `src/knowledge_finder_bot/channels/` | Teams/Telegram formatters |

## Bot Framework Pattern

The bot extends `ActivityHandler` and overrides event handlers:

```python
class NotebookLMBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        # Handle user messages

    async def on_members_added_activity(self, members_added, turn_context):
        # Welcome new users
```

All I/O is async. Use `await` for Bot Framework and Graph API calls.

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
- `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_APP_TENANT_ID`
- `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`

## Implementation Plans

Detailed step-by-step guides:
- **Basic (echo bot):** `docs/plans/2025-02-09-notebooklm-chatbot-basic.md`
- **Advanced (full features):** `docs/plans/2025-02-09-notebooklm-chatbot-advanced.md`
- **Full design:** `docs/plans/notebooklm-chatbot-design.md`
