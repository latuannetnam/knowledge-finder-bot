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
