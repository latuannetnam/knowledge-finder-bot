# Azure Configuration

## App Registrations Required

Two separate Azure AD app registrations:

### 1. Bot Registration
- **Purpose:** Bot Framework authentication (bot identity)
- **Created via:** Azure Bot Service
- **Env vars:**
  - `MICROSOFT_APP_ID`
  - `MICROSOFT_APP_PASSWORD`
  - `MICROSOFT_APP_TENANT_ID`

### 2. Graph API Client
- **Purpose:** Read user groups for ACL
- **Permissions (Application, NOT Delegated):**
  - `User.Read.All`
  - `GroupMember.Read.All`
  - `Directory.Read.All` (optional)
- **Requires:** Admin consent (one-time)
- **Env vars:**
  - `GRAPH_CLIENT_ID`
  - `GRAPH_CLIENT_SECRET`

## Bot Messaging Endpoint

```
https://knowledge-finder-bot.nport.io/api/messages
```

Configure in: Azure Portal → Bot Registration → Configuration → Messaging endpoint

## Environment Variables

```env
# Azure Bot Registration
MICROSOFT_APP_ID=your-bot-app-id
MICROSOFT_APP_PASSWORD=your-bot-app-password
MICROSOFT_APP_TENANT_ID=your-tenant-id

# Graph API Client
GRAPH_CLIENT_ID=your-graph-client-id
GRAPH_CLIENT_SECRET=your-graph-client-secret

# Server
HOST=0.0.0.0
PORT=3978
LOG_LEVEL=INFO
```

## Detailed Setup Guide

See: `docs/plans/azure-app-registration-guide.md`
