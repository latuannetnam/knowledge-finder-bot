# Project Structure

## Directory Layout

```
knowledge-finder-bot/
├── .claude/
│   └── memory/              # Claude memory (this folder)
├── docs/
│   └── plans/
│       ├── notebooklm-chatbot-design.md      # Full design doc
│       ├── 2025-02-09-notebooklm-chatbot-basic.md    # Basic implementation plan
│       └── 2025-02-09-notebooklm-chatbot-advanced.md # Advanced features plan
├── src/
│   └── knowledge_finder_bot/
│       ├── __init__.py
│       ├── config.py        # Pydantic settings
│       ├── main.py          # aiohttp server entrypoint
│       ├── bot/
│       │   ├── __init__.py
│       │   └── bot.py       # create_agent_app() - M365 Agents SDK
│       ├── auth/            # ✅ Azure AD, Graph API (IMPLEMENTED)
│       │   ├── __init__.py
│       │   ├── graph_client.py     # GraphClient with app-only auth
│       │   └── mock_graph_client.py # MockGraphClient for Agent Playground testing
│       ├── acl/             # ✅ Access control (IMPLEMENTED)
│       │   ├── __init__.py
│       │   ├── models.py    # Pydantic models (GroupACL, NotebookACL, ACLConfig)
│       │   └── service.py   # ACLService (get_allowed_notebooks)
│       ├── nlm/             # nlm-proxy client (TODO)
│       └── channels/        # Teams/Telegram formatters (TODO)
├── tests/
│   ├── conftest.py          # Updated with ACL + mock_graph_client fixtures
│   ├── test_config.py       # 3 tests
│   ├── test_bot.py          # 10 tests (includes dual-mode routing tests)
│   ├── test_acl_models.py   # ✅ 11 tests (NEW)
│   ├── test_acl_service.py  # ✅ 14 tests (NEW)
│   └── test_graph_client.py # ✅ 8 tests (NEW)
├── config/
│   └── acl.yaml             # ACL configuration
├── scripts/
│   ├── dev-setup.ps1
│   └── dev-setup.sh
├── pyproject.toml
├── .env.example
└── README.md
```

## Key Files

| File | Purpose |
|------|---------|
| `src/knowledge_finder_bot/main.py` | Server entrypoint, ACL initialization |
| `src/knowledge_finder_bot/bot/bot.py` | `create_agent_app()` factory with ACL injection |
| `src/knowledge_finder_bot/config.py` | Pydantic settings (includes ACL config) |
| `src/knowledge_finder_bot/auth/graph_client.py` | Microsoft Graph API client |\n| `src/knowledge_finder_bot/auth/mock_graph_client.py` | Mock Graph client for Agent Playground |
| `src/knowledge_finder_bot/acl/service.py` | ACL service (group → notebook mapping) |
| `src/knowledge_finder_bot/acl/models.py` | Pydantic models for ACL |
| `config/acl.yaml` | ACL configuration (groups, notebooks, wildcards) |
| `pyproject.toml` | Dependencies, build config |
| `.env` | Local secrets (not in git) |

## Test Coverage (46/46 passing)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_acl_models.py` | 11/11 | 100% |
| `test_acl_service.py` | 14/14 | 100% |
| `test_bot.py` | 10/10 | 89% (includes dual-mode routing tests) |
| `test_graph_client.py` | 8/8 | 98% |
| `test_config.py` | 3/3 | 94% |
