# Development Setup

## Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)**: Extremely fast Python package installer and resolver.
- **[devtunnel](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started)**: Microsoft's tunneling tool for Azure integration (install: `winget install Microsoft.Devtunnels`).
- **[Agent Playground](https://learn.microsoft.com/microsoft-365-copilot/extensibility/debugging-copilot-plugin)**: Official M365 testing tool (install: `npm install -g @microsoft/agents-playground`).

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd knowledge-finder-bot
   ```

2. **Install dependencies:**
   We use `uv` for dependency management. This command creates a virtual environment and installs all required packages.
   ```bash
   uv sync
   ```

3. **Install Claude Code plugins:**
   This project includes custom Claude Code skills for automatic documentation updates.
   ```bash
   # Linux/Mac
   ./scripts/install-plugins.sh

   # Windows
   .\scripts\install-plugins.ps1
   ```

   The script registers the project's local plugin marketplace and installs the `update-docs` plugin.
   After installation, restart Claude Code and verify with `/help | grep update-docs`.

## Environment Configuration

Create a `.env` file in the root directory. You can copy `.env.example` if it exists, or use the template below.

**Critical Note:** This project uses the **Microsoft 365 Agents SDK**, which requires specific environment variable naming conventions (`CONNECTIONS__SERVICE_CONNECTION__...`) different from the legacy Bot Framework SDK.

```ini
# --- M365 Agents SDK Configuration (REQUIRED) ---
# These are used by the SDK to authenticate with Azure Bot Service
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=your-bot-app-id
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=your-bot-app-secret
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=your-tenant-id

# --- Application Settings ---
# Used for internal application logic and Graph API access
MICROSOFT_APP_ID=your-bot-app-id
MICROSOFT_APP_PASSWORD=your-bot-app-secret
MICROSOFT_APP_TENANT_ID=your-tenant-id

GRAPH_CLIENT_ID=your-graph-client-id
GRAPH_CLIENT_SECRET=your-graph-client-secret

# --- Server Configuration ---
HOST=0.0.0.0
PORT=3978
LOG_LEVEL=INFO
```

## Running Locally

1. **Start the bot server:**
   ```bash
   uv run python -m knowledge_finder_bot.main
   ```
   The bot will listen on `http://localhost:3978`.

2. **Start devtunnel (for Azure Bot Service integration):**
   ```powershell
   .\run_devtunnel.ps1
   ```
   This script will:
   - Create a persistent tunnel named `knowledge-finder-bot`
   - Expose your local server via HTTPS
   - Save the endpoint URL to `.devtunnel-endpoint`

   **Important Notes:**
   - If you see "Exiting. Stop the existing host process..." - **this is normal!** Your tunnel is already running from a previous session.
   - The script detects existing tunnels to prevent duplicates
   - Check `.devtunnel-endpoint` file for the active endpoint URL
   - Only restart if you experience actual connectivity issues (see Troubleshooting section)

3. **Test with Agent Playground:**
   ```powershell
   .\run_agentplayground.ps1
   ```
   This script auto-detects the devtunnel endpoint and launches Agent Playground.

4. **Verify Health:**
   ```bash
   curl http://localhost:3978/health
   ```

## Debugging

- **Agent Playground:** The official testing tool for M365 bots. Run `.\run_agentplayground.ps1` for automatic configuration.
- **Logs:** The application uses structured logging. Check the console output for JSON-formatted logs.
- **Devtunnel Status:** Check `.devtunnel-endpoint` file or run `devtunnel show knowledge-finder-bot`.

## Troubleshooting

See [`.claude/memory/debugging.md`](.claude/memory/debugging.md) for comprehensive troubleshooting guide.

### Common Devtunnel Scenarios

**Scenario 1: "Exiting. Stop the existing host process first if you need to restart."**

This is **normal behavior** - your tunnel is already running! The script prevents starting duplicate tunnels.

```powershell
# Check saved endpoint
Get-Content .devtunnel-endpoint

# Verify tunnel is working
devtunnel show knowledge-finder-bot
```

**Scenario 2: Need to restart tunnel**

```powershell
# Stop existing tunnel
Get-Process devtunnel | Stop-Process

# Start fresh tunnel
.\run_devtunnel.ps1
```

**Scenario 3: Tunnel unreachable after inactivity**

The script auto-recovers from stale connections. Just run:

```powershell
.\run_devtunnel.ps1
```

If it detects a stale connection (ghost process), it will automatically delete and recreate the tunnel.
