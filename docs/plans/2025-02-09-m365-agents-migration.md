# Migration: Bot Framework SDK to M365 Agents SDK

**Date:** 2025-02-09
**Status:** Draft
**Author:** Claude Code

## Summary

Migrate from the deprecated Bot Framework SDK (`botbuilder-*`) to the Microsoft 365 Agents SDK (`microsoft-agents-*`). The Bot Framework SDK reaches end-of-life on December 31, 2025.

## Current State

### Dependencies (pyproject.toml)
```toml
"botbuilder-core>=4.14.0",
"botbuilder-integration-aiohttp>=4.14.0",
```

### Key Files
| File | Purpose |
|------|---------|
| `src/knowledge_finder_bot/main.py` | aiohttp server, `BotFrameworkAdapter` |
| `src/knowledge_finder_bot/bot/bot.py` | `ActivityHandler` subclass |

### Current Architecture
```
Request → BotFrameworkAdapter.process_activity() → NotebookLMBot.on_turn()
                                                          ↓
                                              on_message_activity()
                                              on_members_added_activity()
```

## Target State

### New Dependencies
```toml
"microsoft-agents-core",
"microsoft-agents-hosting-aiohttp",
"microsoft-agents-activity",
```

### New Architecture
```
Request → CloudAdapter.process_activity() → AgentApplication
                                                   ↓
                                      @AGENT_APP.activity("message")
                                      @AGENT_APP.activity("conversationUpdate")
```

## Migration Changes

### 1. Package Changes

| Old Package | New Package |
|-------------|-------------|
| `botbuilder-core` | `microsoft-agents-core` |
| `botbuilder-integration-aiohttp` | `microsoft-agents-hosting-aiohttp` |
| `botbuilder-schema` | `microsoft-agents-activity` |

### 2. Import Changes

| Old Import | New Import |
|------------|------------|
| `from botbuilder.core import ActivityHandler, TurnContext` | `from microsoft_agents.core import TurnContext` |
| `from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings` | `from microsoft_agents.hosting.aiohttp import CloudAdapter` |
| `from botbuilder.schema import Activity, ActivityTypes` | `from microsoft_agents.activity import Activity` |

**Note:** Import path uses underscore: `microsoft_agents` (not `microsoft.agents`)

### 3. Bot Class Refactor

#### Before (bot.py)
```python
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity, ActivityTypes

class NotebookLMBot(ActivityHandler):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        user_message = turn_context.activity.text
        await turn_context.send_activity(Activity(...))

    async def on_members_added_activity(self, members_added, turn_context):
        for member in members_added:
            await turn_context.send_activity("Welcome!")
```

#### After (bot.py)
```python
from microsoft_agents.hosting.core import AgentApplication, TurnContext, TurnState, MemoryStorage
from microsoft_agents.hosting.aiohttp import CloudAdapter

from knowledge_finder_bot.config import get_settings

settings = get_settings()

AGENT_APP = AgentApplication[TurnState](
    storage=MemoryStorage(),
    adapter=CloudAdapter()
)

@AGENT_APP.activity("message")
async def on_message_activity(context: TurnContext, state: TurnState) -> None:
    user_message = context.activity.text
    user_name = context.activity.from_property.name or "User"
    echo_text = f"**Echo from {user_name}:** {user_message}"
    await context.send_activity(echo_text)

@AGENT_APP.activity("conversationUpdate")
async def on_members_added(context: TurnContext, state: TurnState) -> None:
    if context.activity.members_added:
        for member in context.activity.members_added:
            if member.id != context.activity.recipient.id:
                await context.send_activity("Hello! I'm the NotebookLM Bot.")

@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception) -> None:
    await context.send_activity("Oops! Something went wrong.")
```

### 4. Main Server Refactor

#### Before (main.py)
```python
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.app_id,
    app_password=settings.app_password,
)
adapter = BotFrameworkAdapter(adapter_settings)
bot = NotebookLMBot(settings)

async def messages(request: web.Request) -> web.Response:
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")
    await adapter.process_activity(activity, auth_header, bot.on_turn)
    return web.Response(status=200)
```

#### After (main.py)
```python
from knowledge_finder_bot.bot import AGENT_APP

async def messages(request: web.Request) -> web.Response:
    return await AGENT_APP.adapter.process_activity(request, AGENT_APP)

def create_app() -> web.Application:
    app = web.Application()
    app["agent_app"] = AGENT_APP
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    return app
```

### 5. Test Updates

Update test imports and mocks:

```python
# Before
from botbuilder.core import TurnContext
from unittest.mock import MagicMock

# After
from microsoft_agents.core import TurnContext
from unittest.mock import AsyncMock
```

## Implementation Steps

1. **Update pyproject.toml** - Replace botbuilder packages with microsoft-agents packages
2. **Run `uv sync`** - Install new dependencies
3. **Refactor bot.py** - Convert class-based to decorator-based pattern
4. **Refactor main.py** - Use CloudAdapter and AgentApplication
5. **Update tests** - Fix imports and mocks
6. **Test locally** - Verify echo bot works
7. **Test with Teams** - Verify end-to-end via nport tunnel

## Key Differences Summary

| Aspect | Bot Framework | M365 Agents SDK |
|--------|---------------|-----------------|
| Pattern | Class inheritance (`ActivityHandler`) | Decorator-based (`@AGENT_APP.activity`) |
| State | Manual handling | Built-in `TurnState` |
| Adapter | `BotFrameworkAdapter` | `CloudAdapter` |
| Activity parsing | Manual `Activity().deserialize()` | Automatic |
| Handler signature | `(self, turn_context)` | `(context, state)` |

## Testing Strategy

1. **Unit tests** - Mock `TurnContext` and verify handler behavior
2. **Integration test** - Start server, send HTTP request to `/api/messages`
3. **E2E test** - Connect via nport, test in Teams

## Sources

- [microsoft-agents-hosting-aiohttp (PyPI)](https://pypi.org)
- [CloudAdapter Documentation (Microsoft Learn)](https://microsoft.com)
- [ActivityHandler Documentation (Microsoft Learn)](https://microsoft.com)
- [Quickstart: Create and test a basic agent (Microsoft Learn)](https://microsoft.com)
- [microsoft/Agents-for-python (GitHub)](https://github.com)
