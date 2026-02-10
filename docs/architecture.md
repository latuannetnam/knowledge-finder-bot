# System Architecture

## Overview

The Knowledge Finder Bot is a bridge between Microsoft Teams/Telegram users and Google's NotebookLM, allowing users to query curated knowledge bases using natural language.

## High-Level Data Flow

```mermaid
graph TD
    User[User (Teams/Telegram)] -->|Message| Azure[Azure Bot Service]
    Azure -->|Webhook| Bot[Bot Backend (aiohttp:3978)]

    subgraph "Knowledge Finder Bot"
        Bot --> Auth[Auth Middleware]
        Auth -->|Validate Token| Bot

        Bot --> Graph[Graph API Client]
        Graph -->|Get Groups| MSGraph[Microsoft Graph]

        Bot --> ACL[ACL Service]
        ACL -->|Map Groups to Notebooks| Config[ACL Config]

        Bot --> Proxy[nlm-proxy Client]
        Proxy -->|Query specific notebooks| NLM[NotebookLM (via nlm-proxy)]
    end

    Proxy -->|Response| Bot
    Bot -->|Reply| User
```

## Key Components

### 1. Bot Server & Handler (`src/knowledge_finder_bot/bot/`)
- Built using the **Microsoft 365 Agents SDK** (formerly Bot Framework SDK).
- Handles incoming activities (messages, member updates).
- Uses `aiohttp` for the web server.

### 2. Authentication (`src/knowledge_finder_bot/auth/`)
- Validates JWT tokens from Azure Bot Service.
- Manages authentication with Microsoft Graph API using App-only permissions (client credentials flow).

### 3. ACL Service (`src/knowledge_finder_bot/acl/`)
- Maps Azure AD security groups to NotebookLM notebook IDs.
- Ensures users can only query notebooks they are authorized to access.

### 4. nlm-proxy Integration (`src/knowledge_finder_bot/nlm/`)
- **NLMClient**: Wraps the OpenAI Python SDK (`AsyncOpenAI`) to communicate with nlm-proxy
  - Streaming responses with SSE chunk buffering
  - Non-streaming fallback support
  - Conversation ID extraction from `system_fingerprint` (format: `conv_{id}`)
  - Per-request ACL via `extra_body.metadata.allowed_notebooks`
- **SessionStore**: Multi-turn conversation management
  - TTLCache with 24-hour expiry (default)
  - Maps Azure AD Object ID → conversation ID
- **Response Formatter**: Source attribution in responses
  - Extracts notebook info from `reasoning_content`
  - Adds markdown-formatted source citations
- **Bot Integration**: Graceful fallback and error handling
  - Typing indicator before queries
  - Falls back to echo mode when nlm-proxy not configured
  - User-friendly error messages

## Technology Stack Decisions

- **Dependency Management: `uv`**
  - Chosen for speed and reliability over pip/poetry.
  - Simplifies environment setup and dependency resolution.

- **Framework: Microsoft 365 Agents SDK**
  - The legacy Bot Framework SDK (v4) is nearing EOL.
  - This project uses the modern, lightweight Agents SDK designed for Copilot extensions.

- **Logging: `structlog`**
  - All logs are structured JSON for easier ingestion into observability tools.
  - Enforces consistent context (user ID, request ID) across log entries.

- **Tunneling: `devtunnel`**
  - Microsoft-native tunneling solution for Azure Bot Service development
  - Persistent subdomain eliminates need to update bot configuration

- **nlm-proxy Client: OpenAI SDK**
  - Uses `AsyncOpenAI` for OpenAI-compatible API (nlm-proxy)
  - Supports both streaming (default) and non-streaming modes
  - Custom `extra_body` parameter for per-request metadata (ACL)
