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
