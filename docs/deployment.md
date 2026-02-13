# Deployment & Infrastructure

## Azure Configuration

### 1. Bot Registration (Azure Bot Service)
1. Create a "Azure Bot" resource in the Azure Portal.
2. Select "Multi Tenant" or "Single Tenant" based on your needs.
3. Obtain the **App ID** and **App Secret**.
4. Configure the Messaging Endpoint to your deployed URL (e.g., `https://your-bot.azurewebsites.net/api/messages`).

### 2. App Registration (for Graph API)
*Separate from the Bot identity, though they can theoretically share an App ID, separating them is often cleaner.*

1. Create a new App Registration in Entra ID (Azure AD).
2. **API Permissions:**
   - `GroupMember.Read.All` (Application permission) - To check user group membership.
   - `User.Read.All` (Application permission) - To look up user details.
3. Grant Admin Consent for the permissions.
4. Create a Client Secret.

## Hosting

### Docker
*Coming soon.*

### Azure Web App (Python)
1. Create an App Service (Linux, Python 3.11).
2. Configure Environment Variables in "Settings > Environment variables".
3. Deploy code using GitHub Actions or Azure CLI.
   ```bash
   az webapp up --runtime PYTHON:3.11 --sku B1 --logs
   ```

### Ubuntu 24.04 (Systemd)

Recommended for production on a VPS or dedicated server.

#### 1. Prerequisites
Update system and install basic tools. Ubuntu 24.04 includes Python 3.12 by default.
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl acl
```

#### 2. Create Service User
Create a dedicated user `kbot` for security.
```bash
sudo useradd -m -s /bin/bash kbot
sudo loginctl enable-linger kbot
```

#### 3. Install uv (as kbot)
Switch to the user and install `uv`.
```bash
sudo su - kbot
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

#### 4. Clone and Install
```bash
git clone https://github.com/latuannetnam/knowledge-finder-bot.git
cd knowledge-finder-bot

# Install production dependencies
uv sync --frozen
```

#### 5. Configuration
Create the `.env` file.
```bash
cp .env.example .env
nano .env
# Fill in:
# - CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*
# - GRAPH_CLIENT_*
# - NLM_PROXY_*
```

#### 6. Systemd Service
Exit to root (`exit`) and create the service file.

`sudo nano /etc/systemd/system/knowledge-finder-bot.service`

```ini
[Unit]
Description=Knowledge Finder Bot
After=network.target

[Service]
Type=simple
User=kbot
Group=kbot
WorkingDirectory=/home/kbot/knowledge-finder-bot
# Use the virtual environment created by uv
ExecStart=/home/kbot/.local/bin/uv run python -m knowledge_finder_bot.main
Environment="PATH=/home/kbot/.local/bin:/usr/local/bin:/usr/bin:/bin"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### 7. Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now knowledge-finder-bot.service
sudo systemctl status knowledge-finder-bot.service
```

#### 8. Verify
Check logs to ensure successful startup.
```bash
sudo journalctl -u knowledge-finder-bot.service -f
```
