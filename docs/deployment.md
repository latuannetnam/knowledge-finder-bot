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
Create a dedicated user `ubuntu` for security.
```bash
sudo useradd -m -s /bin/bash ubuntu
sudo loginctl enable-linger ubuntu
```

#### 3. Install uv (as ubuntu)
Switch to the user and install `uv`.
```bash
sudo su - ubuntu
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
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/knowledge-finder-bot
# Load variables from the .env file
EnvironmentFile=/home/ubuntu/knowledge-finder-bot/.env
# Use the virtual environment created by uv
ExecStart=/home/ubuntu/.local/bin/uv run python -m knowledge_finder_bot.main
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"
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

#### 9. Troubleshooting

**Error: `Failed to determine user credentials`**
- **Cause:** The `User=ubuntu` specified in `knowledge-finder-bot.service` does not exist.
- **Fix:**
  1. Create the user as instructed in step 2:
     ```bash
     sudo useradd -m -s /bin/bash ubuntu
     ```
  2. OR, update the service file to use your current user (e.g., `ubuntu`):
     Update `/etc/systemd/system/knowledge-finder-bot.service`:
     ```ini
     [Service]
     User=ubuntu
     Group=ubuntu
     WorkingDirectory=/home/ubuntu/knowledge-finder-bot
     ExecStart=/home/ubuntu/.local/bin/uv run python -m knowledge_finder_bot.main
     Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"
     ```

     Then verify paths exist and restart service:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl restart knowledge-finder-bot
     ```

**Error: `status=203/EXEC`**
- **Cause:** Systemd cannot find the executable specified in `ExecStart`. This usually means the path to `uv` is incorrect.
- **Fix:**
  1. Find the correct path to `uv` for your user:
     ```bash
     which uv
     # Example output: /home/ubuntu/.local/bin/uv
     ```
  2. Update `ExecStart` in the service file to match this exact path.
  3. Ensure the `WorkingDirectory` path is also correct.
  4. Run `sudo systemctl daemon-reload && sudo systemctl restart knowledge-finder-bot`
