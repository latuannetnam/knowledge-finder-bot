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
│       ├── nlm/             # ✅ nlm-proxy client + STREAMING (IMPLEMENTED)
│       │   ├── __init__.py
│       │   ├── models.py    # NLMChunk (streaming), NLMResponse (buffered)
│       │   ├── client.py    # NLMClient with query_stream() AsyncGenerator + query()
│       │   ├── formatter.py # format_response() + format_source_attribution()
│       │   └── session.py   # SessionStore for multi-turn conversations
│       └── channels/        # Teams/Telegram formatters (TODO)
├── tests/
│   ├── conftest.py          # Updated with ACL + nlm fixtures
│   ├── test_config.py       # 3 tests
│   ├── test_bot.py          # 10 tests (includes dual-mode routing tests)
│   ├── test_acl_models.py   # ✅ 11 tests
│   ├── test_acl_service.py  # ✅ 14 tests
│   ├── test_graph_client.py # ✅ 8 tests
│   ├── test_nlm_client.py   # ✅ 8 tests (streaming, non-streaming, extra_body)
│   ├── test_nlm_streaming.py # ✅ 9 tests (NEW - query_stream, NLMChunk)
│   ├── test_nlm_session.py  # ✅ 6 tests (TTL, get/set/clear)
│   ├── test_nlm_formatter.py # ✅ 9 tests (format_response + format_source_attribution)
│   └── test_bot_nlm.py      # ✅ 9 tests (REWRITTEN - StreamingResponse integration)
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
| `src/knowledge_finder_bot/bot/bot.py` | `create_agent_app()` with StreamingResponse integration |
| `src/knowledge_finder_bot/config.py` | Pydantic settings (includes ACL config) |
| `src/knowledge_finder_bot/auth/graph_client.py` | Microsoft Graph API client |\n| `src/knowledge_finder_bot/auth/mock_graph_client.py` | Mock Graph client for Agent Playground |
| `src/knowledge_finder_bot/acl/service.py` | ACL service (group → notebook mapping) |
| `src/knowledge_finder_bot/acl/models.py` | Pydantic models for ACL |
| `config/acl.yaml` | ACL configuration (groups, notebooks, wildcards) |
| `pyproject.toml` | Dependencies, build config |
| `.env` | Local secrets (not in git) |

## Test Coverage (87/87 passing) ✅

| Test File | Tests | Module Coverage |
|-----------|-------|-----------------|
| `test_acl_models.py` | 11/11 | acl/models.py: 100% |
| `test_acl_service.py` | 14/14 | acl/service.py: 100% |
| `test_bot.py` | 10/10 | bot/bot.py: ACL routing |
| `test_graph_client.py` | 8/8 | auth/graph_client.py: 98% |
| `test_nlm_client.py` | 8/8 | nlm/client.py: query() buffered |
| `test_nlm_streaming.py` | 9/9 | nlm/client.py: query_stream() + NLMChunk |
| `test_nlm_session.py` | 6/6 | nlm/session.py: 100% |
| `test_nlm_formatter.py` | 9/9 | nlm/formatter.py: 100% |
| `test_bot_nlm.py` | 9/9 | bot/bot.py: StreamingResponse integration |
| `test_config.py` | 3/3 | config.py: 96% |

**Streaming implementation:** All 15 new tests passing (9 streaming + 4 formatter + 2 model)
