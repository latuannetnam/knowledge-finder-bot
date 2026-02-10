# nlm-proxy Integration Plan (Bot-Side Only)

**Date:** 2025-02-10
**Branch:** `feature/nlm-proxy-integration`
**Status:** Planning
**Prerequisite:** ACL mechanism complete (46/46 tests), nlm-proxy per-request ACL available (separate plan)

---

## Context

The bot currently echoes messages back with ACL info (allowed notebooks). This plan replaces the echo logic with real queries to **nlm-proxy**, an OpenAI-compatible proxy for NotebookLM.

**Out of scope:** nlm-proxy per-request `metadata.allowed_notebooks` support — tracked separately in the nlm-proxy repo.

**Assumption:** nlm-proxy accepts `metadata.allowed_notebooks` in `POST /v1/chat/completions` requests and filters the smart router's notebook candidates accordingly.

**Decisions made:**
- Use streaming (SSE) with typing indicator + buffered response
- Implement multi-turn via `conversation_id` (NotebookLM manages context server-side)
- Plain markdown formatting first (no Adaptive Cards yet)
- Graceful fallback to echo mode when nlm-proxy is not configured

---

## nlm-proxy API Contract (reference)

```
POST /v1/chat/completions
Authorization: Bearer <api-key>

{
  "model": "knowledge-finder",
  "messages": [{"role": "user", "content": "..."}],
  "stream": true,
  "conversation_id": "optional-for-multi-turn",
  "metadata": {"allowed_notebooks": ["uuid1", "uuid2"]}
}
```

- Streaming: SSE chunks with `reasoning_content` (OpenAI o1/o3 format) + `content`
- `conversation_id` returned in `system_fingerprint` field as `conv_{id}`
- Non-streaming: standard `ChatCompletionResponse` with `reasoning_content` in message

---

## Step 1: Add OpenAI SDK dependency

**File:** `pyproject.toml`

Add `"openai>=1.59.0"` to `dependencies`. Run `uv add openai`.

---

## Step 2: Configuration

### 2.1 Update config.py

**File:** `src/knowledge_finder_bot/config.py` — add after `test_user_groups` (line 34):

```python
# nlm-proxy (empty defaults = optional, graceful fallback to echo)
nlm_proxy_url: str = Field("", alias="NLM_PROXY_URL")
nlm_proxy_api_key: str = Field("", alias="NLM_PROXY_API_KEY")
nlm_model_name: str = Field("knowledge-finder", alias="NLM_MODEL_NAME")
nlm_timeout: float = Field(60.0, alias="NLM_TIMEOUT")
nlm_session_ttl: int = Field(86400, alias="NLM_SESSION_TTL")
nlm_session_maxsize: int = Field(1000, alias="NLM_SESSION_MAXSIZE")
```

### 2.2 Update .env.example

Add `NLM_PROXY_URL`, `NLM_PROXY_API_KEY`, `NLM_MODEL_NAME`, `NLM_TIMEOUT`, session settings.

### 2.3 Update tests/conftest.py

Add `NLM_PROXY_URL` and `NLM_PROXY_API_KEY` (empty strings) to `mock_env_vars` fixture.

---

## Step 3: Create nlm/ module

### 3.1 Create nlm/models.py

**File:** `src/knowledge_finder_bot/nlm/models.py`

```python
class NLMResponse(BaseModel):
    answer: str                         # Main response content
    reasoning: str | None = None        # From reasoning_content (router decision)
    model: str                          # Model used (e.g., "knowledge-finder")
    conversation_id: str | None = None  # For multi-turn (from system_fingerprint)
    finish_reason: str | None = None
```

### 3.2 Create nlm/client.py

**File:** `src/knowledge_finder_bot/nlm/client.py`

Core class `NLMClient`:
- Constructor: `AsyncOpenAI(base_url=settings.nlm_proxy_url, api_key=settings.nlm_proxy_api_key, timeout=settings.nlm_timeout)`
- Method: `async def query(user_message, allowed_notebooks, conversation_id=None, stream=True) -> NLMResponse`
- Uses `extra_body={"metadata": {"allowed_notebooks": [...]}, "conversation_id": ...}`
- **Streaming** (default): buffer chunks, extract `reasoning_content` + `content`, parse `conversation_id` from `system_fingerprint` field (format: `conv_{id}`)
- **Non-streaming** (fallback): direct response parsing
- structlog logging at start/complete/error (no f-strings)

### 3.3 Create nlm/formatter.py

**File:** `src/knowledge_finder_bot/nlm/formatter.py`

Function `format_response(response: NLMResponse, acl_service: ACLService | None) -> str`:
- Returns plain markdown (works in Agent Playground, Teams, Telegram)
- Main answer text + optional `---\n*Source: {notebook_name}*`

### 3.4 Create nlm/session.py

**File:** `src/knowledge_finder_bot/nlm/session.py`

Class `SessionStore`:
- `TTLCache(maxsize, ttl)` mapping `aad_object_id -> conversation_id`
- Methods: `get(aad_id)`, `set(aad_id, conv_id)`, `clear(aad_id)`
- Reuses `cachetools.TTLCache` (already a dependency)

### 3.5 Create nlm/__init__.py

Export `NLMClient`, `NLMResponse`.

---

## Step 4: Bot Handler Integration

### 4.1 Modify bot.py

**File:** `src/knowledge_finder_bot/bot/bot.py`

Update `create_agent_app()` signature (line 37):
```python
def create_agent_app(
    settings, graph_client=None, acl_service=None, mock_graph_client=None,
    nlm_client=None, session_store=None,  # NEW
)
```

Replace echo logic (lines 180-190):
```python
if nlm_client is None:
    # existing echo code (fallback)
    return

# Send typing indicator
await context.send_activity(Activity(type=ActivityTypes.typing))

# Multi-turn: retrieve existing conversation_id
conversation_id = session_store.get(aad_object_id) if session_store else None

try:
    nlm_response = await nlm_client.query(
        user_message=user_message,
        allowed_notebooks=list(allowed_notebooks),
        conversation_id=conversation_id,
    )
    # Store for next turn
    if nlm_response.conversation_id and session_store:
        session_store.set(aad_object_id, nlm_response.conversation_id)

    formatted = format_response(nlm_response, acl_service)
    await context.send_activity(formatted)
except Exception as e:
    logger.error("nlm_query_failed", error=str(e))
    await context.send_activity("I encountered an error. Please try again.")
```

### 4.2 Modify main.py

**File:** `src/knowledge_finder_bot/main.py`

In `create_app()` (after ACL init, before `create_agent_app()` call):
```python
nlm_client = None
session_store = None
if settings.nlm_proxy_url and settings.nlm_proxy_api_key:
    from knowledge_finder_bot.nlm import NLMClient
    from knowledge_finder_bot.nlm.session import SessionStore
    nlm_client = NLMClient(settings)
    session_store = SessionStore(ttl=settings.nlm_session_ttl, maxsize=settings.nlm_session_maxsize)
```

Pass both to `create_agent_app()`.

---

## Step 5: Tests

### test_nlm_client.py
- Non-streaming query success (mock `AsyncOpenAI.chat.completions.create`)
- Streaming query success (mock async iterator of chunks)
- `allowed_notebooks` passed correctly in `extra_body.metadata`
- `conversation_id` passed and extracted from `system_fingerprint`
- Error handling (exception -> log + re-raise)

### test_nlm_session.py
- get/set basic operations
- TTL expiry
- clear session
- Missing key returns None

### test_nlm_formatter.py
- Format with answer only
- Format with source attribution
- Format with no acl_service

### test_bot_nlm.py
- Message handler queries nlm-proxy when nlm_client configured
- Falls back to echo when nlm_client is None
- Multi-turn: conversation_id stored and reused
- Error: nlm-proxy failure -> user-friendly message
- Typing indicator sent before query

---

## Implementation Sequence

| # | Task | Files |
|---|------|-------|
| 1 | Add dependency | `pyproject.toml` + `uv sync` |
| 2 | Config | `config.py`, `.env.example`, `conftest.py` |
| 3 | nlm/ module | `models.py`, `client.py`, `formatter.py`, `session.py`, `__init__.py` |
| 4 | Handler integration | `bot.py`, `main.py` |
| 5 | Tests | `test_nlm_client.py`, `test_nlm_session.py`, `test_nlm_formatter.py`, `test_bot_nlm.py` |
| 6 | Verify | Run tests + manual E2E |

---

## Verification

### Automated
```bash
uv run pytest tests/ -v
uv run pytest --cov=knowledge_finder_bot tests/
```

### Manual E2E (requires nlm-proxy per-request ACL to be deployed)
1. Start nlm-proxy: `cd D:\latuan\Programming\nlm-proxy && uv run nlm-proxy openai`
2. Start bot: `uv run python -m knowledge_finder_bot.main`
3. Start tunnel: `nport 3978 -s knowledge-finder-bot`
4. Agent Playground: send query -> verify real answer (not echo)
5. Send follow-up -> verify multi-turn context maintained
6. Verify typing indicator appears before response

---

## Files Summary

| File | Action |
|------|--------|
| `pyproject.toml` | Modify — add `openai` dependency |
| `src/knowledge_finder_bot/config.py` | Modify — add nlm-proxy settings |
| `src/knowledge_finder_bot/nlm/__init__.py` | Create |
| `src/knowledge_finder_bot/nlm/models.py` | Create |
| `src/knowledge_finder_bot/nlm/client.py` | Create |
| `src/knowledge_finder_bot/nlm/formatter.py` | Create |
| `src/knowledge_finder_bot/nlm/session.py` | Create |
| `src/knowledge_finder_bot/bot/bot.py` | Modify — replace echo with nlm query |
| `src/knowledge_finder_bot/main.py` | Modify — init NLMClient + SessionStore |
| `tests/conftest.py` | Modify — add nlm env vars |
| `tests/test_nlm_client.py` | Create |
| `tests/test_nlm_session.py` | Create |
| `tests/test_nlm_formatter.py` | Create |
| `tests/test_bot_nlm.py` | Create |
| `.env.example` | Modify — add nlm-proxy vars |
