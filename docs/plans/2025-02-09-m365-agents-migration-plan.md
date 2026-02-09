# Migration: Bot Framework SDK → M365 Agents SDK

## Context

The Bot Framework SDK (`botbuilder-*`) reaches end-of-life on December 31, 2025. Microsoft recommends migrating to the M365 Agents SDK (`microsoft-agents-*`) for continued support and new features. This migration converts the current class-based `ActivityHandler` pattern to the decorator-based `AgentApplication` pattern.

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Replace botbuilder deps with microsoft-agents |
| `src/knowledge_finder_bot/bot/__init__.py` | Export `create_agent_app` instead of `NotebookLMBot` |
| `src/knowledge_finder_bot/bot/bot.py` | Rewrite: class → decorator pattern |
| `src/knowledge_finder_bot/main.py` | Use `CloudAdapter` instead of `BotFrameworkAdapter` |
| `tests/test_bot.py` | Update fixtures and test invocations |

## Implementation Steps

### Step 1: Update Dependencies

**File:** `pyproject.toml`

Replace:
```toml
"botbuilder-core>=4.14.0",
"botbuilder-integration-aiohttp>=4.14.0",
```

With:
```toml
"microsoft-agents-core",
"microsoft-agents-hosting-aiohttp",
"microsoft-agents-activity",
```

Run: `uv sync`

### Step 2: Rewrite Bot Module

**File:** `src/knowledge_finder_bot/bot/bot.py`

Convert from class-based to decorator-based:

```python
from microsoft_agents.hosting.core import AgentApplication, TurnContext, TurnState, MemoryStorage

def create_agent_app(settings: Settings) -> AgentApplication[TurnState]:
    app = AgentApplication[TurnState](storage=MemoryStorage())
    app.settings = settings

    @app.activity("message")
    async def on_message(context: TurnContext, state: TurnState) -> None:
        user_message = context.activity.text
        user_name = context.activity.from_property.name or "User"
        echo_text = f"**Echo from {user_name}:** {user_message}"
        await context.send_activity(echo_text)

    @app.activity("conversationUpdate")
    async def on_members_added(context: TurnContext, state: TurnState) -> None:
        for member in context.activity.members_added or []:
            if member.id != context.activity.recipient.id:
                await context.send_activity("Hello! I'm the NotebookLM Bot...")

    return app
```

**File:** `src/knowledge_finder_bot/bot/__init__.py`

```python
from knowledge_finder_bot.bot.bot import create_agent_app
__all__ = ["create_agent_app"]
```

### Step 3: Update Main Entry Point

**File:** `src/knowledge_finder_bot/main.py`

Key changes:
- Import `CloudAdapter` from `microsoft_agents.hosting.aiohttp`
- Import `create_agent_app` instead of `NotebookLMBot`
- Replace `BotFrameworkAdapter` with `CloudAdapter`
- Use `adapter.process(request, agent_app)` instead of manual activity parsing

```python
from microsoft_agents.hosting.aiohttp import CloudAdapter
from knowledge_finder_bot.bot import create_agent_app

adapter = CloudAdapter()
agent_app = create_agent_app(settings)

async def messages(request):
    return await adapter.process(request, agent_app)
```

### Step 4: Update Tests

**File:** `tests/test_bot.py`

- Replace `NotebookLMBot` fixture with `agent_app` fixture using `create_agent_app()`
- Add `mock_turn_state` fixture
- Update test calls from `bot.on_message_activity(context)` to `agent_app.on_turn(context, state)`
- Set `context.activity.type` to route to correct handler

### Step 5: Verify

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Start server
uv run python -m knowledge_finder_bot.main

# Health check
curl http://localhost:3978/health

# Test with Teams (separate terminal)
nport 3978 -s knowledge-finder-bot
```

## Key Pattern Changes

| Aspect | Before | After |
|--------|--------|-------|
| Bot definition | `class NotebookLMBot(ActivityHandler)` | `AgentApplication[TurnState]` |
| Handler registration | Override `on_message_activity` | `@app.activity("message")` |
| Handler signature | `(self, turn_context)` | `(context, state)` |
| Members added | Separate method parameter | `context.activity.members_added` |
| Adapter | `BotFrameworkAdapter` | `CloudAdapter` |

## Potential Issues

1. **Package names may differ** - Verify actual PyPI package names after `uv sync`
2. **Import paths** - Use `microsoft_agents` (underscore) not `microsoft.agents`
3. **CloudAdapter.process() signature** - May need adjustment based on actual SDK

## Integration Testing

### Option 1: Local Testing with Agents Playground

The Bot Framework Emulator is deprecated (archived December 2025). Use **Microsoft Agents Playground** instead.

**Installation (choose one):**

```bash
# Windows (winget)
winget install agentsplayground

# npm (cross-platform)
npm install -g @microsoft/m365agentsplayground

# Linux
curl -s https://raw.githubusercontent.com/OfficeDev/microsoft-365-agents-toolkit/dev/.github/scripts/install-agentsplayground-linux.sh | bash
```

**Testing steps:**

1. Start the bot server:
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```

2. Launch Agents Playground and connect to `http://localhost:3978/api/messages`

3. Test scenarios:
   - Send a message → verify echo response
   - New conversation → verify welcome message
   - Check markdown formatting in responses

**Sources:**
- [Agents Playground Documentation](https://microsoft.com)
- [Agents Toolkit GitHub](https://github.com)

### Option 2: MS Teams Integration with Nport

Use [Nport](https://github.com/tuanngocptn/nport) to expose local server to the internet for Teams testing.

**Prerequisites:**
- Azure Bot registration configured
- Bot endpoint set to `https://knowledge-finder-bot.nport.io/api/messages`

**Testing steps:**

1. Start the bot server:
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```

2. Start Nport tunnel (separate terminal):
   ```bash
   nport 3978 -s knowledge-finder-bot
   ```

   This exposes `localhost:3978` at `https://knowledge-finder-bot.nport.io`

3. Verify tunnel is working:
   ```bash
   curl https://knowledge-finder-bot.nport.io/health
   # Expected: {"status": "healthy"}
   ```

4. Test in Microsoft Teams:
   - Open Teams desktop or web app
   - Find the bot in Apps or start a chat with it
   - Send a message → verify echo response
   - Verify welcome message appears on first interaction

**Nport advantages over ngrok:**
- Free persistent subdomain (`knowledge-finder-bot.nport.io`)
- No session time limits
- Simple CLI: `nport <port> -s <subdomain>`

## Verification Checklist

- [ ] `uv sync` succeeds with new packages
- [ ] `uv run pytest tests/ -v` all tests pass
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Echo bot works in Agents Playground (local)
- [ ] Nport tunnel exposes bot correctly
- [ ] Echo bot works in MS Teams via nport tunnel
- [ ] Welcome message displays for new conversations
