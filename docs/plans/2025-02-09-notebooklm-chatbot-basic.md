# NotebookLM Chatbot - Basic Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up project foundation with Bot Framework, Azure AD authentication, and a basic echo bot for MS Teams.

**Architecture:** Python Bot Framework application with aiohttp server, Pydantic settings, and basic Azure AD token validation. The bot echoes user messages back as a proof-of-concept before adding nlm-proxy integration.

**Tech Stack:** Python 3.11+, uv (package manager), botbuilder-python, aiohttp, pydantic-settings, msal, structlog

---

## Task 1: Project Structure Setup

**Files:**
- Create: `src/knowledge_finder_bot/__init__.py`
- Create: `src/knowledge_finder_bot/config.py`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "nlm-chatbot"
version = "0.1.0"
description = "NotebookLM chatbot for MS Teams and Telegram"
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

[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/knowledge_finder_bot"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Testing
.coverage
htmlcov/
.pytest_cache/

# Logs
*.log
logs/
```

**Step 3: Create .env.example**

```env
# Azure Bot Registration
MICROSOFT_APP_ID=your-bot-app-id
MICROSOFT_APP_PASSWORD=your-bot-app-password
MICROSOFT_APP_TENANT_ID=your-tenant-id

# Graph API Client (for user group lookup)
GRAPH_CLIENT_ID=your-graph-client-id
GRAPH_CLIENT_SECRET=your-graph-client-secret

# Server
HOST=0.0.0.0
PORT=3978

# Logging
LOG_LEVEL=INFO
```

**Step 4: Create src/knowledge_finder_bot/__init__.py**

```python
"""NotebookLM Chatbot - MS Teams and Telegram bot for NotebookLM queries."""

__version__ = "0.1.0"
```

**Step 5: Create src/knowledge_finder_bot/config.py**

```python
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

    # Azure Bot Registration
    app_id: str = Field(..., alias="MICROSOFT_APP_ID")
    app_password: str = Field(..., alias="MICROSOFT_APP_PASSWORD")
    app_tenant_id: str = Field(..., alias="MICROSOFT_APP_TENANT_ID")

    # Graph API Client
    graph_client_id: str = Field(..., alias="GRAPH_CLIENT_ID")
    graph_client_secret: str = Field(..., alias="GRAPH_CLIENT_SECRET")

    # Server
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(3978, alias="PORT")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")


def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()
```

**Step 6: Sync dependencies with uv**

Run: `uv sync`
Expected: Dependencies installed, `.venv` created automatically

**Step 7: Verify project structure**

Run: `uv run python -c "from knowledge_finder_bot.config import get_settings; print('Config module OK')"`
Expected: `Config module OK`

**Step 8: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/
git commit -m "feat: initialize project structure with Pydantic settings

- Add pyproject.toml with dependencies
- Add Pydantic settings configuration
- Add .env.example template

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Basic Bot Class (Echo Bot)

**Files:**
- Create: `src/knowledge_finder_bot/bot/__init__.py`
- Create: `src/knowledge_finder_bot/bot/bot.py`

**Step 1: Create src/knowledge_finder_bot/bot/__init__.py**

```python
"""Bot module."""

from knowledge_finder_bot.bot.bot import NotebookLMBot

__all__ = ["NotebookLMBot"]
```

**Step 2: Create src/knowledge_finder_bot/bot/bot.py (Echo version)**

```python
"""Main bot class - Echo implementation for testing."""

import structlog
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()


class NotebookLMBot(ActivityHandler):
    """NotebookLM Bot - currently echoes messages for testing.

    This basic implementation verifies Bot Framework integration works
    before adding nlm-proxy and Azure AD functionality.
    """

    def __init__(self, settings: Settings):
        """Initialize bot with settings.

        Args:
            settings: Application configuration
        """
        self.settings = settings

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle incoming messages by echoing them back.

        Args:
            turn_context: The turn context for this turn of the conversation
        """
        user_message = turn_context.activity.text
        user_name = turn_context.activity.from_property.name or "User"

        logger.info(
            "message_received",
            user_name=user_name,
            message_preview=user_message[:50] if user_message else "",
        )

        # Echo the message back
        echo_text = f"**Echo from {user_name}:** {user_message}"

        await turn_context.send_activity(
            Activity(
                type=ActivityTypes.message,
                text=echo_text,
                text_format="markdown",
            )
        )

    async def on_members_added_activity(
        self,
        members_added: list,
        turn_context: TurnContext,
    ) -> None:
        """Welcome new users to the conversation.

        Args:
            members_added: List of members added to the conversation
            turn_context: The turn context for this turn
        """
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_text = (
                    "Hello! I'm the NotebookLM Bot.\n\n"
                    "Currently running in **echo mode** for testing.\n"
                    "Send me a message and I'll echo it back!"
                )
                await turn_context.send_activity(welcome_text)
```

**Step 3: Verify bot module imports**

Run: `uv run python -c "from knowledge_finder_bot.bot import NotebookLMBot; print('Bot module OK')"`
Expected: `Bot module OK`

**Step 4: Commit**

```bash
git add src/knowledge_finder_bot/bot/
git commit -m "feat: add basic echo bot implementation

- Add NotebookLMBot with echo functionality
- Add welcome message for new users
- Prepare structure for future Azure AD integration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Application Entrypoint

**Files:**
- Create: `src/knowledge_finder_bot/main.py`

**Step 1: Create src/knowledge_finder_bot/main.py**

```python
"""Application entrypoint - aiohttp server with Bot Framework."""

import sys

import structlog
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from knowledge_finder_bot.bot import NotebookLMBot
from knowledge_finder_bot.config import get_settings

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def messages(request: web.Request) -> web.Response:
    """Handle incoming Bot Framework messages.

    Args:
        request: The incoming HTTP request from Bot Framework

    Returns:
        HTTP response (usually empty 200 for Bot Framework)
    """
    if request.content_type != "application/json":
        return web.Response(status=415)

    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    adapter: BotFrameworkAdapter = request.app["adapter"]
    bot: NotebookLMBot = request.app["bot"]

    try:
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200)
    except Exception as e:
        logger.exception("Error processing activity", error=str(e))
        return web.Response(status=500)


async def health(request: web.Request) -> web.Response:
    """Health check endpoint.

    Args:
        request: The incoming HTTP request

    Returns:
        JSON response with health status
    """
    return web.json_response({"status": "healthy"})


def create_app() -> web.Application:
    """Create and configure the aiohttp application.

    Returns:
        Configured aiohttp Application
    """
    settings = get_settings()

    # Create Bot Framework adapter
    adapter_settings = BotFrameworkAdapterSettings(
        app_id=settings.app_id,
        app_password=settings.app_password,
    )
    adapter = BotFrameworkAdapter(adapter_settings)

    # Create bot
    bot = NotebookLMBot(settings)

    # Create app
    app = web.Application()
    app["adapter"] = adapter
    app["bot"] = bot
    app["settings"] = settings

    # Add routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the bot server."""
    settings = get_settings()

    logger.info(
        "starting_bot_server",
        host=settings.host,
        port=settings.port,
    )

    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
```

**Step 2: Verify main module imports**

Run: `uv run python -c "from knowledge_finder_bot.main import create_app; print('Main module OK')"`
Expected: `Main module OK`

**Step 3: Commit**

```bash
git add src/knowledge_finder_bot/main.py
git commit -m "feat: add aiohttp server entrypoint

- Add Bot Framework adapter setup
- Add /api/messages endpoint for bot traffic
- Add /health endpoint for Kubernetes probes
- Configure structlog for logging

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Basic Tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Create: `tests/test_bot.py`

**Step 1: Create tests/__init__.py**

```python
"""Test suite for nlm-chatbot."""
```

**Step 2: Create tests/conftest.py**

```python
"""Pytest fixtures for nlm-chatbot tests."""

import os
from unittest.mock import patch

import pytest

from knowledge_finder_bot.config import Settings


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "MICROSOFT_APP_ID": "test-app-id",
        "MICROSOFT_APP_PASSWORD": "test-app-password",
        "MICROSOFT_APP_TENANT_ID": "test-tenant-id",
        "GRAPH_CLIENT_ID": "test-graph-client-id",
        "GRAPH_CLIENT_SECRET": "test-graph-client-secret",
        "HOST": "127.0.0.1",
        "PORT": "3978",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def settings(mock_env_vars) -> Settings:
    """Create Settings instance with mocked environment."""
    return Settings()
```

**Step 3: Create tests/test_config.py**

```python
"""Tests for configuration module."""

import pytest

from knowledge_finder_bot.config import Settings


def test_settings_loads_from_env(settings: Settings):
    """Test that settings loads values from environment variables."""
    assert settings.app_id == "test-app-id"
    assert settings.app_password == "test-app-password"
    assert settings.app_tenant_id == "test-tenant-id"


def test_settings_has_defaults(settings: Settings):
    """Test that settings has correct default values."""
    assert settings.host == "127.0.0.1"
    assert settings.port == 3978
    assert settings.log_level == "DEBUG"
```

**Step 4: Create tests/test_bot.py**

```python
"""Tests for bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.bot import NotebookLMBot
from knowledge_finder_bot.config import Settings


@pytest.fixture
def bot(settings: Settings) -> NotebookLMBot:
    """Create bot instance for testing."""
    return NotebookLMBot(settings)


@pytest.fixture
def mock_turn_context():
    """Create a mock turn context for testing."""
    context = AsyncMock()
    context.activity = MagicMock()
    context.activity.text = "Hello, bot!"
    context.activity.from_property = MagicMock()
    context.activity.from_property.name = "Test User"
    context.activity.recipient = MagicMock()
    context.activity.recipient.id = "bot-id"
    return context


@pytest.mark.asyncio
async def test_on_message_activity_echoes_message(bot, mock_turn_context):
    """Test that bot echoes user messages."""
    await bot.on_message_activity(mock_turn_context)

    mock_turn_context.send_activity.assert_called_once()
    call_args = mock_turn_context.send_activity.call_args
    activity = call_args[0][0]
    assert "Hello, bot!" in activity.text
    assert "Test User" in activity.text


@pytest.mark.asyncio
async def test_on_members_added_sends_welcome(bot, mock_turn_context):
    """Test that bot sends welcome message to new members."""
    member = MagicMock()
    member.id = "new-user-id"

    await bot.on_members_added_activity([member], mock_turn_context)

    mock_turn_context.send_activity.assert_called_once()
    welcome_text = mock_turn_context.send_activity.call_args[0][0]
    assert "NotebookLM Bot" in welcome_text
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add tests/
git commit -m "test: add unit tests for config and bot modules

- Add pytest fixtures for mocked settings
- Add tests for Settings configuration loading
- Add tests for bot echo and welcome functionality

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Development Setup Script

**Files:**
- Create: `scripts/dev-setup.ps1` (Windows)
- Create: `scripts/dev-setup.sh` (Unix)

**Step 1: Create scripts/dev-setup.ps1**

```powershell
# Development setup script for Windows

Write-Host "Setting up nlm-chatbot development environment..." -ForegroundColor Green

# Check Python version
$pythonVersion = python --version 2>&1
if ($pythonVersion -notmatch "Python 3\.1[1-9]") {
    Write-Host "Error: Python 3.11+ required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}
Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan

# Create virtual environment if not exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -e ".[dev]"

# Copy .env.example if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env with your Azure credentials" -ForegroundColor Cyan
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env with your Azure Bot credentials"
Write-Host "  2. Run: python -m knowledge_finder_bot.main"
Write-Host "  3. Use Bot Framework Emulator to test"
```

**Step 2: Create scripts/dev-setup.sh**

```bash
#!/bin/bash
# Development setup script for Unix

set -e

echo -e "\033[32mSetting up nlm-chatbot development environment...\033[0m"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ ! $PYTHON_VERSION =~ "Python 3.1"[1-9] ]]; then
    echo -e "\033[31mError: Python 3.11+ required. Found: $PYTHON_VERSION\033[0m"
    exit 1
fi
echo -e "\033[36mPython version: $PYTHON_VERSION\033[0m"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo -e "\033[33mCreating virtual environment...\033[0m"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "\033[33mActivating virtual environment...\033[0m"
source .venv/bin/activate

# Install dependencies
echo -e "\033[33mInstalling dependencies...\033[0m"
pip install -e ".[dev]"

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\033[33mCreating .env from .env.example...\033[0m"
    cp .env.example .env
    echo -e "\033[36mPlease edit .env with your Azure credentials\033[0m"
fi

echo -e "\n\033[32mSetup complete!\033[0m"
echo -e "\033[36mNext steps:\033[0m"
echo "  1. Edit .env with your Azure Bot credentials"
echo "  2. Run: python -m knowledge_finder_bot.main"
echo "  3. Use Bot Framework Emulator to test"
```

**Step 3: Commit**

```bash
git add scripts/
git commit -m "chore: add development setup scripts

- Add PowerShell script for Windows
- Add Bash script for Unix/Mac
- Scripts create venv, install deps, setup .env

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: README Documentation

**Files:**
- Create: `README.md`

**Step 1: Create README.md**

```markdown
# NotebookLM Chatbot

MS Teams and Telegram chatbot for querying NotebookLM notebooks via nlm-proxy.

## Status

**Current:** Echo bot implementation (Phase 1)

## Quick Start

### Prerequisites

- Python 3.11+
- Azure Bot registration (for Teams deployment)
- Bot Framework Emulator (for local testing)

### Development Setup

**Windows:**
```powershell
.\scripts\dev-setup.ps1
```

**Unix/Mac:**
```bash
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh
```

### Running Locally

1. Edit `.env` with your Azure Bot credentials
2. Start the bot:
   ```bash
   python -m knowledge_finder_bot.main
   ```
3. Open Bot Framework Emulator
4. Connect to `http://localhost:3978/api/messages`

### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
nlm-chatbot/
├── src/knowledge_finder_bot/
│   ├── __init__.py
│   ├── config.py          # Pydantic settings
│   ├── main.py            # Application entrypoint
│   └── bot/
│       ├── __init__.py
│       └── bot.py         # Bot implementation
├── tests/
│   ├── conftest.py        # Test fixtures
│   ├── test_config.py     # Config tests
│   └── test_bot.py        # Bot tests
├── scripts/
│   ├── dev-setup.ps1      # Windows setup
│   └── dev-setup.sh       # Unix setup
├── pyproject.toml
├── .env.example
└── README.md
```

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start guide

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Verification Checklist

After completing all tasks, verify the basic implementation:

1. **Install and run tests:**
   ```bash
   uv sync
   uv run pytest tests/ -v
   ```

2. **Start the server:**
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```

3. **Health check:**
   ```bash
   curl http://localhost:3978/health
   ```
   Expected: `{"status": "healthy"}`

---

## Task 7: Local Testing with Bot Framework Emulator

**Goal:** Test the bot locally using Microsoft's Bot Framework Emulator before deploying to Teams.

### Step 1: Install Bot Framework Emulator

**Windows:**
1. Download the latest release from: https://github.com/microsoft/BotFramework-Emulator/releases
2. Download the `.exe` installer (e.g., `BotFramework-Emulator-4.14.1-windows-setup.exe`)
3. Run the installer and follow the prompts
4. Launch "Bot Framework Emulator" from Start Menu

**macOS:**
1. Download the `.dmg` file from the releases page
2. Open the `.dmg` and drag to Applications folder
3. Launch from Applications (may need to allow in Security & Privacy settings)

**Linux:**
1. Download the `.AppImage` file from the releases page
2. Make it executable: `chmod +x BotFramework-Emulator-*.AppImage`
3. Run: `./BotFramework-Emulator-*.AppImage`

### Step 2: Connect Emulator to Local Bot

1. Start your bot server:
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```
   You should see: `starting_bot_server host=0.0.0.0 port=3978`

2. Open Bot Framework Emulator

3. Click "Open Bot" or File → Open Bot

4. Enter the Bot URL:
   ```
   http://localhost:3978/api/messages
   ```

5. Leave "Microsoft App ID" and "Microsoft App Password" **empty** for local testing
   (These are only needed when connecting to Azure-deployed bots)

6. Click "Connect"

### Step 3: Test the Echo Bot

1. In the Emulator chat window, type a message: `Hello bot!`
2. Verify you receive an echo response: `**Echo from User:** Hello bot!`
3. Check the "Log" panel on the right for request/response details
4. Verify your terminal shows the `message_received` log entry

### Step 4: Troubleshooting Emulator Issues

| Issue | Solution |
|-------|----------|
| "Cannot connect to bot" | Ensure bot is running on port 3978 |
| "Unauthorized" error | Clear App ID/Password fields for local testing |
| No response from bot | Check terminal for Python errors |
| CORS errors | Emulator handles this automatically |

---

## Task 8: MS Teams Integration Testing with Nport

**Goal:** Expose your local bot to the internet with a persistent subdomain so MS Teams can send messages to it during development.

**Why Nport?** Unlike ngrok (which changes URL on restart with free tier), Nport provides persistent custom subdomains for free.

### Step 1: Install Nport

**Option A: Global installation (recommended)**
```bash
npm install -g nport
```

**Option B: Run without installing**
```bash
npx nport 3978 -s knowledge-finder-bot
```

### Step 2: Start Nport Tunnel with Custom Subdomain

1. First, start your bot:
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```

2. In a **new terminal**, start Nport with your custom subdomain:
   ```bash
   nport 3978 -s knowledge-finder-bot
   ```

3. Nport will display your persistent URL:
   ```
   https://knowledge-finder-bot.nport.io -> http://localhost:3978
   ```

4. Your bot messaging endpoint is now:
   ```
   https://knowledge-finder-bot.nport.io/api/messages
   ```

### Step 3: Nport CLI Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `port` | Local port to tunnel | `nport 3978` |
| `-s` / `--subdomain` | Custom subdomain (persistent) | `nport 3978 -s knowledge-finder-bot` |
| `-b` / `--backend` | Custom backend URL (temporary) | `nport 3978 -b https://custom.backend` |
| `--set-backend` | Save backend URL permanently | `nport --set-backend https://custom.backend` |
| `-l` / `--language` | Set language (en/vi) | `nport 3978 -l en` |
| `-v` / `--version` | Show version | `nport -v` |

### Step 4: Configure Azure Bot with Nport URL

1. Go to Azure Portal → Your Bot Registration → Configuration

2. Update the **Messaging endpoint**:
   ```
   https://knowledge-finder-bot.nport.io/api/messages
   ```

3. Click "Apply" / "Save"

4. **This URL is persistent** - you don't need to update Azure every time you restart Nport!

### Step 5: Update .env for Azure Bot Testing

When testing with Teams (not Emulator), you need real Azure credentials:

```env
# Azure Bot Registration (from Azure Portal)
MICROSOFT_APP_ID=your-actual-app-id-from-azure
MICROSOFT_APP_PASSWORD=your-actual-app-password-from-azure
MICROSOFT_APP_TENANT_ID=your-tenant-id
```

### Step 6: Test in MS Teams

1. Ensure bot is running with Azure credentials:
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```

2. Ensure Nport is running:
   ```bash
   nport 3978 -s knowledge-finder-bot
   ```

3. In MS Teams:
   - Go to Apps → Upload a custom app (if app manifest is ready)
   - Or: Chat → Search for your bot by name
   - Send a message to the bot

4. Verify the echo response appears in Teams

### Step 7: Nport Configuration File

Nport stores settings in `~/.nport/config.json`. You can set default backend permanently:

```bash
nport --set-backend https://your-custom-backend.com
```

### Troubleshooting Nport + Teams

| Issue | Solution |
|-------|----------|
| "Subdomain already taken" | Choose a different subdomain name |
| "401 Unauthorized" from Teams | Verify MICROSOFT_APP_ID and PASSWORD match Azure Portal |
| "502 Bad Gateway" | Your local bot isn't running or crashed |
| Teams shows "Something went wrong" | Check bot terminal for error logs |
| Connection refused | Ensure bot is running on port 3978 |

### Alternative Tunneling Tools

If Nport doesn't work for your setup:

| Tool | Command | Notes |
|------|---------|-------|
| **ngrok** | `ngrok http 3978` | URL changes on restart (free tier) |
| **Cloudflare Tunnel** | `cloudflared tunnel --url http://localhost:3978` | Free, requires Cloudflare account |
| **localtunnel** | `npx localtunnel --port 3978 --subdomain knowledge-finder-bot` | Free, subdomain may not persist |
| **VS Code Dev Tunnels** | Built into VS Code | Good for VS Code users |

---

## Next Steps

After verifying the basic implementation works, proceed to the advanced plan:
- `docs/plans/2025-02-09-notebooklm-chatbot-advanced.md`
