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

### 4. [nlm-proxy](https://github.com/latuannetnam/nlm-proxy) Integration (`src/knowledge_finder_bot/nlm/`)
- **NLMClient** (Hybrid approach — see ADR-012):
  - **`AsyncOpenAI`** (raw SDK) for query/streaming — preserves `reasoning_content` from SSE deltas
  - **`ChatOpenAI`** (LangChain) for rewrite/followup — message-based features only needing `content`
  - Per-request ACL via `extra_body.metadata.allowed_notebooks`
  - **Session Isolation**: Uses Teams `conversation.id` as `chat_id` and `session_id`
    - Each conversation (personal, group, channel) gets isolated session history
    - `aad_object_id` is used only for ACL enforcement and user identification
- **ConversationMemoryManager**: Per-session conversation history
  - TTLCache with configurable TTL (default: 1 hour) and maxsize (default: 1000)
  - Stores Q&A exchanges for multi-turn context
  - Sessions keyed by `conversation.id` for proper isolation
- **Question Rewriting**: Automatic follow-up disambiguation
  - Rewrites follow-up questions as standalone using conversation history
  - Uses nlm-proxy's `llm_task` route (triggered by `### Task:` prefix)
- **Follow-up Suggestions**: Post-answer question generation (see ADR-013)
  - Generates 3 suggested follow-up questions
  - Displayed as **HeroCard** with vertical buttons in Teams
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

- **[nlm-proxy](https://github.com/latuannetnam/nlm-proxy) Client: Hybrid AsyncOpenAI + ChatOpenAI**
  - `AsyncOpenAI` (raw SDK) for query/streaming — direct access to `reasoning_content` in SSE deltas
  - `ChatOpenAI` (LangChain) for rewrite/followup — leverages LangChain message types
  - Conversation memory via `langchain-core` message types
  - LLM-powered question rewriting and follow-up generation via `### Task:` routing
