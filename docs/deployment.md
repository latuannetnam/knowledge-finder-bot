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
