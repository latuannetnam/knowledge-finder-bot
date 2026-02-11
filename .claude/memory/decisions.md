# Architecture Decisions

## Decision Log

Record significant architecture decisions with rationale.

---

### ADR-001: Use uv instead of pip/venv

**Date:** 2025-02-09

**Decision:** Use `uv` as the package manager.

**Rationale:**
- 10-100x faster than pip
- Better dependency resolution
- `[dependency-groups]` syntax for dev deps
- Creates `.venv` automatically with `uv sync`
- Single tool for venv + deps

**Consequences:**
- Team must have `uv` installed
- Use `uv run` prefix for all commands

---

### ADR-002: Use Nport instead of ngrok

**Date:** 2025-02-09

**Decision:** Use Nport for local tunnel to Teams.

**Rationale:**
- Persistent subdomain for free (`knowledge-finder-bot.nport.io`)
- No account required
- No URL changes on restart
- Simple: `nport 3978 -s knowledge-finder-bot`

**Consequences:**
- Requires npm/npx
- Less known than ngrok (but simpler)

---

### ADR-003: OpenAI SDK before LangGraph

**Date:** 2025-02-09

**Decision:** Start with direct OpenAI SDK for nlm-proxy integration.

**Rationale:**
- nlm-proxy is OpenAI-compatible
- Minimal dependencies (~2MB vs ~100MB)
- Simple debugging, shallow stack traces
- Native streaming support

**Migration triggers to LangGraph:**
- Need conversation memory beyond nlm-proxy sessions
- Need multi-step reasoning workflows
- Need to call multiple backends

---

### ADR-004: App-only Graph API permissions

**Date:** 2025-02-09

**Decision:** Use application permissions (not delegated) for Microsoft Graph.

**Rationale:**
- No user consent dialogs
- No SSO token exchange complexity
- No per-user token expiry issues
- Centralized admin control

**Consequences:**
- Requires admin consent (one-time)
- Bot can read any user's groups (by design for ACL)

---

### ADR-005: M365 Agents SDK over Bot Framework SDK

**Date:** 2025-02-09

**Decision:** Migrate from Bot Framework SDK to M365 Agents SDK.

**Rationale:**
- Bot Framework SDK EOL: December 31, 2025
- M365 Agents SDK is the official successor
- Better TypeScript/Python parity
- Decorator-based message handlers (cleaner code)
- Active development and support

**Consequences:**
- Requires different env var format (`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*`)
- Must use `create_agent_app()` factory pattern
- Breaking change from legacy bot code

**Implementation:** Completed in commit `dbeed4c` (4/4 tests passing)

---

### ADR-006: Dependency Injection for ACL Components

**Date:** 2025-02-10

**Decision:** Use factory function `create_agent_app()` with optional GraphClient/ACLService parameters.

**Rationale:**
- Testability: Easy to mock dependencies in tests
- Flexibility: Supports dual-mode (echo/ACL)
- Graceful degradation: Falls back to echo mode if ACL unavailable
- Separation of concerns: ACL logic isolated from bot logic

**Consequences:**
- No module-level globals
- Dependencies must be initialized in `main.py`
- Test fixtures require explicit dependency injection

**Implementation:** Completed in commits `5206eed` → `cf59c42` (42/42 tests passing)

---

### ADR-007: TTLCache over Redis for User Info

**Date:** 2025-02-10

**Decision:** Use in-memory TTLCache (cachetools) instead of Redis.

**Rationale:**
- Simpler deployment (no Redis server needed)
- 5-minute TTL sufficient for AD group changes
- 1000-user capacity adequate for most orgs
- Zero network latency
- No serialization overhead

**Migration triggers to Redis:**
- Multi-instance deployment (need shared cache)
- User base > 10,000 users
- Need persistent cache across restarts

**Implementation:** Completed in commit `e611733`

---

### ADR-008: YAML over JSON for ACL Configuration

**Date:** 2025-02-10

**Decision:** Use YAML (`config/acl.yaml`) for ACL configuration.

**Rationale:**
- Human-friendly: Comments, multi-line strings
- Fewer syntax errors (no trailing commas)
- Better for config files (not data exchange)
- Native support for complex structures

**Consequences:**
- Requires `pyyaml` dependency
- Must validate with Pydantic models
- Hot-reload support via `reload_config()`

**Implementation:** Completed in commit `6428e9b`

---

### ADR-009: Dual-Mode Routing for Agent Playground Testing

**Date:** 2025-02-10

**Decision:** Implement dual-mode routing that automatically detects fake AAD IDs from Agent Playground and routes them to MockGraphClient, while routing real AAD IDs to the real Graph API client.

**Rationale:**
- Agent Playground uses fake AAD IDs (`00000000-0000-0000-0000-*`) that cause Graph API 404 errors
- Need to test ACL logic in Agent Playground without Azure AD setup
- Both development (Agent Playground) and production (Teams/Telegram) should work simultaneously
- Per-request routing enables seamless testing without configuration changes
- MockGraphClient provides deterministic group memberships via `TEST_USER_GROUPS` env var

**Implementation:**
- `TEST_MODE=true` enables MockGraphClient creation alongside real GraphClient
- `_is_fake_aad_id()` detects the `00000000-0000-0000-0000-` prefix pattern
- Per-request routing in `on_message()` handler selects appropriate client
- Test groups defined in `config/acl.yaml` (Admin: 11111111..., HR: 22222222..., Eng: 33333333...)
- Falls back gracefully when only one client is available

**Consequences:**
- Both real and mock clients can coexist in memory
- Adds 4 new dual-mode routing tests (46/46 tests total)
- Enables ACL testing in Agent Playground with simulated group memberships
- No configuration changes needed when switching between Agent Playground and Teams
- `TEST_USER_GROUPS` env var controls which groups the mock user belongs to

**Implementation:** Completed (10/10 bot tests passing)

---

### ADR-010: End-to-End Streaming with M365 StreamingResponse

**Date:** 2025-02-10

**Decision:** Implement real-time streaming from nlm-proxy to users via M365 Agents SDK `StreamingResponse` instead of buffering the entire response.

**Rationale:**
- **User Experience:** Users see thinking process and answer as it arrives (no 5-30 second blocking wait)
- **Transparency:** Reasoning visible in real-time, source attribution clear
- **Status Updates:** Informative updates show which notebook is being searched
- **Channel Agnostic:** Works on Teams, DirectLine, and non-streaming channels with same code
- **M365 SDK Native:** `StreamingResponse` handles batching and channel-specific intervals automatically
- **Performance:** Reduces perceived latency by showing progress immediately

**Implementation:**
- Created `NLMChunk` dataclass for streaming chunks (`reasoning`, `content`, `meta`)
- Implemented `query_stream()` AsyncGenerator on `NLMClient` that yields chunks in real-time
- Added `format_source_attribution()` helper for streaming use case
- Rewrote bot handler to use `StreamingResponse`:
  - `queue_informative_update()` for notebook name status
  - `queue_text_chunk()` for reasoning, separator, content, and source attribution
  - `await end_stream()` to finalize message
- Session management preserves conversation ID for multi-turn

**Consequences:**
- Added 15 new tests (9 streaming + 4 formatter + 2 model) - total: 87/87 passing
- Removed `Activity` and `ActivityTypes` imports (no longer needed)
- Backward compatible: echo fallback when nlm_client=None still works
- Non-streaming channels accumulate chunks and send once (handled by SDK)
- Error handling: graceful degradation via streaming or fallback to send_activity

**Architecture Flow:**
```
BEFORE: User → typing indicator → await query() [blocks 5-30s] → send_activity(full_text)

AFTER:  User → StreamingResponse(context)
             → queue_informative_update("Searching HR Docs...")
             → queue_text_chunk(reasoning_delta)         [streamed]
             → queue_text_chunk("\n\n---\n\n")            [separator]
             → queue_text_chunk(content_delta)            [streamed]
             → queue_text_chunk("\n---\n*Source: HR Docs*") [attribution]
             → await end_stream()
```

**Implementation:** Completed in commits `97de6ef` → `ab77068` (87/87 tests passing)

---

### ADR-012: Adaptive Cards for Reasoning Content

**Date:** 2025-02-11

**Decision:** Use Adaptive Cards with `Action.ToggleVisibility` to display reasoning content, rather than streaming it directly as plain text.

**Rationale:**
- **User Focus:** Users primarily want the answer. Raw reasoning text (which can be verbose) distracts from the final response.
- **Transparency:** We still want to expose the reasoning for trust/verification, but keep it optional.
- **UI Experience:** A collapsible "Show reasoning" section keeps the chat history clean while preserving the "thinking" context.
- **Streaming Compatibility:** We can accumulate reasoning chunks during the stream and attach the card at the end (or update it in place if supported, but attachment at end is safer for V1).

**Implementation:**
- **Streaming Mode:** Reasoning chunks are accumulated in memory. When stream ends, an Adaptive Card attachment is added to the message.
- **Buffered Mode:** Same approach—reasoning text is collected and attached to the final `Activity`.
- **Truncation:** Reasoning text is truncated at 15,000 characters to fit within Adaptive Card limits.

**Consequences:**
- Requires `microsoft-agents-activity` (already present).
- Adds `formatter.py` logic for card construction.
- Reasoning is not streamed token-by-token *visually* to the user (it's hidden/accumulated), only the status update ("Analyzing...") is shown. The answer *is* streamed.

**Implementation:** Completed (5/5 formatter tests passing).


```markdown
### ADR-XXX: [Title]

**Date:** YYYY-MM-DD

**Decision:** [What we decided]

**Rationale:**
- [Reason 1]
- [Reason 2]

**Consequences:**
- [Consequence 1]
- [Consequence 2]
```
