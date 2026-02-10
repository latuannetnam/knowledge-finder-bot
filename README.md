# Knowledge Finder Bot

**A Microsoft Teams & Telegram chatbot that answers questions using Google's NotebookLM with Azure AD-based access control.**

[![Status](https://img.shields.io/badge/Status-nlm--proxy_Complete-success)](./docs/architecture.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](./pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-72%2F72_passing-brightgreen)](./tests/)
[![Coverage](https://img.shields.io/badge/Coverage-77%25-green)](./tests/)

This bot allows users to query curated knowledge bases (NotebookLM notebooks) directly from their chat interface. It handles authentication, enforces notebook-level access control via Azure AD groups, and routes queries to the appropriate notebook.

## ✨ Features

- ✅ **Azure AD Integration** - Authenticate users via Microsoft Teams
- ✅ **Access Control Lists (ACL)** - Control notebook access by AD group membership
- ✅ **Wildcard Patterns** - Support public notebooks and admin groups
- ✅ **Dual-Mode Routing** - Test ACL in Agent Playground without Azure AD setup
- ✅ **Graceful Fallback** - Echo mode when ACL/nlm-proxy unavailable
- ✅ **Caching** - 5-minute TTL cache for Graph API calls (reduces API load by ~95%)
- ✅ **M365 Agents SDK** - Modern Microsoft bot framework
- ✅ **NotebookLM Integration** - Query notebooks via nlm-proxy with streaming responses
- ✅ **Multi-turn Conversations** - 24-hour session cache for context retention
- ✅ **Source Attribution** - Responses include notebook source citations

## 🚀 Quick Start

```bash
# 1. Install dependencies (requires Python 3.11+)
uv sync

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Configure ACL (optional, falls back to echo mode)
# Edit config/acl.yaml with your AD group IDs

# 4. Run the bot
uv run python -m knowledge_finder_bot.main

# 5. Run tests
uv run pytest tests/ -v
```

## 📋 Prerequisites

- **Python 3.11+** - Required for modern type hints
- **uv** - Fast Python package manager (`pip install uv`)
- **Azure Bot Registration** - For Teams integration
- **Azure AD App Registration** - For Graph API access (optional, for ACL)

## 🏗️ Architecture

```
User (Teams) → Azure Bot Service → Bot Backend (aiohttp:3978)
                                          ↓
                        ┌──── Auth Middleware (Bot Framework JWT) ────┐
                        │                                              │
                        ↓                                              ↓
            ┌─── Graph API Client ───┐               ┌─── ACL Service ───┐
            │ GET /users/{id}/memberOf│               │ Map groups →      │
            │ Returns: AD group list  │               │   notebooks       │
            │ (cached 5min, 1000 users)│               │ (config/acl.yaml) │
            └─────────────┬────────────┘               └────────┬──────────┘
                          │                                     │
                          └──────────── Check Access ───────────┘
                                        ↓
                          ┌─── nlm-proxy Client ────┐
                          │ POST /v1/chat/completions│
                          │ model: knowledge-finder  │
                          │ metadata: allowed_notebooks │
                          │ Streaming: SSE responses │
                          └──────────┬───────────────┘
                                     ↓
                          ┌─── SessionStore ────────┐
                          │ Multi-turn conversations│
                          │ TTL: 24 hours           │
                          └──────────┬──────────────┘
                                     ↓
                              Format \u0026 Send Response
```

## 📂 Repository Structure

```
knowledge-finder-bot/
├── .claude/
│   └── memory/              # Claude memory system
├── docs/
│   ├── plans/               # Implementation plans
│   └── architecture.md      # System architecture
├── src/
│   └── knowledge_finder_bot/
│       ├── acl/             # ✅ Access Control Lists
│       │   ├── models.py    # Pydantic models (GroupACL, NotebookACL)
│       │   └── service.py   # ACL logic (get_allowed_notebooks)
│       ├── auth/            # ✅ Authentication
│       │   ├── graph_client.py     # Microsoft Graph API client
│       │   └── mock_graph_client.py # Mock client for Agent Playground
│       ├── nlm/             # ✅ nlm-proxy Integration
│       │   ├── models.py    # NLMResponse Pydantic model
│       │   ├── client.py    # NLMClient with AsyncOpenAI
│       │   ├── formatter.py # Response formatter with source attribution
│       │   └── session.py   # SessionStore for multi-turn conversations
│       ├── bot/             # ✅ Bot handler
│       │   └── bot.py       # create_agent_app() factory
│       ├── config.py        # ✅ Pydantic settings
│       └── main.py          # ✅ aiohttp server entrypoint
├── tests/                   # ✅ 72/72 tests passing
│   ├── test_acl_models.py   # 11 tests (100% coverage)
│   ├── test_acl_service.py  # 14 tests (100% coverage)
│   ├── test_graph_client.py # 8 tests (98% coverage)
│   ├── test_nlm_client.py   # 8 tests (100% coverage)
│   ├── test_nlm_session.py  # 6 tests (100% coverage)
│   ├── test_nlm_formatter.py # 5 tests (100% coverage)
│   ├── test_bot_nlm.py      # 7 tests (integration)
│   ├── test_config.py       # 3 tests (96% coverage)
│   └── test_bot.py          # 10 tests (90% coverage, includes dual-mode)
├── config/
│   └── acl.yaml             # ✅ ACL configuration
├── pyproject.toml           # Dependencies (uv)
├── CLAUDE.md                # Guidance for Claude Code
└── README.md                # This file
```

## 🔒 Access Control (ACL)

The bot enforces notebook-level access control using Azure AD group memberships:

```yaml
# config/acl.yaml
notebooks:
  # Admin wildcard - access to ALL notebooks
  - id: "*"
    name: "All Notebooks"
    allowed_groups:
      - group_id: "99999999-aaaa-bbbb-cccc-dddddddddddd"
        display_name: "IT Admins"

  # Regular notebook with specific groups
  - id: "hr-notebook"
    name: "HR Docs"
    allowed_groups:
      - group_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        display_name: "HR Team"

  # Public notebook - all authenticated users
  - id: "public-notebook"
    name: "Public KB"
    allowed_groups:
      - "*"  # Wildcard = all users
```

**Wildcard Patterns:**
- `allowed_groups: ["*"]` → Notebook accessible to ALL authenticated users
- `id: "*"` → Groups listed can access ALL notebooks (admin/superuser pattern)

## 🧪 Testing & Development

### Test Mode for Agent Playground

The bot supports **dual-mode routing** to test ACL logic in Agent Playground without Azure AD:

```bash
# Enable TEST_MODE in .env
TEST_MODE=true
TEST_USER_GROUPS=22222222-2222-2222-2222-222222222222,33333333-3333-3333-3333-333333333333
```

**How it works:**
1. Agent Playground sends fake AAD IDs like `00000000-0000-0000-0000-0000000000020`
2. Bot detects the `00000000-0000-0000-0000-*` prefix pattern
3. Fake IDs → MockGraphClient (uses `TEST_USER_GROUPS`)
4. Real AAD IDs → Real Graph API client
5. Both modes coexist — automatic per-request routing

**Test Groups** (defined in `config/acl.yaml`):
- `11111111-1111-1111-1111-111111111111` - Test Admin (all notebooks)
- `22222222-2222-2222-2222-222222222222` - Test HR (hr-notebook + public)
- `33333333-3333-3333-3333-333333333333` - Test Engineering (engineering-notebook + public)

See `.env.example` for complete TEST_MODE examples.

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=knowledge_finder_bot

# Run specific test file
uv run pytest tests/test_nlm_client.py -v
```

**Test Results:** 72/72 tests passing (100% success rate)
- ACL Models: 11/11 (100% coverage)
- ACL Service: 14/14 (100% coverage)
- Graph API Client: 8/8 (98% coverage)
- nlm-proxy Client: 8/8 (100% coverage)
- nlm-proxy Session: 6/6 (100% coverage)
- nlm-proxy Formatter: 5/5 (100% coverage)
- Bot Integration (nlm): 7/7 (integration tests)
- Bot Integration (ACL): 10/10 (90% coverage, includes dual-mode routing)
- Config: 3/3 (96% coverage)

## 📖 Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Guidance for Claude Code (architecture, patterns, commands)
- **[Setup Guide](./docs/setup.md)** - Installation and local development
- **[Architecture](./docs/architecture.md)** - System design and components
- **[ACL Implementation Plan](./docs/plans/2025-02-10-acl-mechanism.md)** - Step-by-step ACL guide

## 🚦 Project Status

### ✅ Completed (February 2025)

**M365 Agents SDK Migration** (commit `dbeed4c`)
- Migrated from Bot Framework SDK to M365 Agents SDK v0.7.0
- Decorator-based message handlers
- Factory pattern with dependency injection

**ACL Mechanism** (commits `5206eed` → `cf59c42`)
- Microsoft Graph API client with app-only authentication
- ACL service with YAML-based configuration
- Pydantic models with GUID validation
- Bot handler with ACL enforcement and graceful fallback
- **Dual-mode routing**: Fake AAD IDs → MockGraphClient, real IDs → Graph API
- MockGraphClient for Agent Playground testing without Azure AD
- TTLCache for user info (5-min TTL, 1000 users)

**nlm-proxy Integration** (branch `feature/nlm-proxy-integration`)
- NLMClient with AsyncOpenAI SDK
  - Streaming responses with SSE chunk buffering
  - Non-streaming fallback
  - Conversation ID extraction from `system_fingerprint`
  - `extra_body` for per-request ACL metadata
- SessionStore for multi-turn conversations (24-hour TTL)
- Response formatter with source attribution
- Bot integration with typing indicator and error handling
- Comprehensive test suite (72/72 tests passing, 77% coverage)

### ⏳ Next Phase

**Production Deployment**
- Manual E2E testing with nlm-proxy
- Azure deployment configuration
- Monitoring and observability setup

## 🔧 Environment Variables

```bash
# M365 Agents SDK (required for Teams integration)
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=your-bot-app-id
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=your-bot-password
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=your-tenant-id

# Graph API (required for ACL)
GRAPH_CLIENT_ID=your-graph-app-id
GRAPH_CLIENT_SECRET=your-graph-secret

# ACL Configuration (optional, defaults shown)
ACL_CONFIG_PATH=config/acl.yaml
GRAPH_CACHE_TTL=300
GRAPH_CACHE_MAXSIZE=1000

# Test Mode (Agent Playground testing)
TEST_MODE=false
TEST_USER_GROUPS=

# nlm-proxy Integration (optional, falls back to echo mode)
NLM_PROXY_URL=
NLM_PROXY_API_KEY=
NLM_MODEL_NAME=knowledge-finder
NLM_TIMEOUT=60
NLM_SESSION_TTL=86400
NLM_SESSION_MAXSIZE=1000

# Server Configuration
HOST=0.0.0.0
PORT=3978
LOG_LEVEL=INFO
```

See `.env.example` for a complete template.

## 🤝 Contributing

See [CONTRIBUTING.md](./docs/contributing.md) for coding standards and testing guidelines.

## 📄 License

MIT

---

**Built with:** Python 3.11+ • M365 Agents SDK • Microsoft Graph API • Pydantic • structlog
