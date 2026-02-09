# Code Patterns & Conventions

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Package | `snake_case` | `knowledge_finder_bot` |
| Module | `snake_case` | `graph_client.py` |
| Class | `PascalCase` | `NotebookLMBot` |
| Function | `snake_case` | `get_allowed_notebooks` |
| Constant | `UPPER_SNAKE` | `GRAPH_API_BASE` |

## Async Patterns

All I/O operations are async:

```python
async def on_message_activity(self, turn_context: TurnContext) -> None:
    """Handle incoming messages."""
    # Always await I/O
    await turn_context.send_activity(response)
```

## Configuration Pattern

Use Pydantic settings with env aliases:

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_id: str = Field(..., alias="MICROSOFT_APP_ID")
```

## Logging Pattern

Use structlog with context:

```python
import structlog
logger = structlog.get_logger()

logger.info("message_received", user_name=name, message_preview=text[:50])
```

## Bot Framework Pattern

Extend `ActivityHandler`, override `on_*` methods:

```python
from botbuilder.core import ActivityHandler, TurnContext

class NotebookLMBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        pass

    async def on_members_added_activity(self, members_added, turn_context) -> None:
        pass
```

## Testing Pattern

Use pytest-asyncio with fixtures:

```python
@pytest.fixture
def settings(mock_env_vars) -> Settings:
    return Settings()

@pytest.mark.asyncio
async def test_something(settings):
    pass
```
