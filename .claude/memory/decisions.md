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

## Template for New Decisions

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
