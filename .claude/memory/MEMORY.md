# Knowledge Finder Bot - Claude Memory

> **Structure:** Modular memory with topic-specific files. Keep this index under 200 lines.

## 🔄 Memory Update Reminder

**⚠️ IMPORTANT: Update this memory after:**
- ✅ Completing major implementation tasks (new modules, features)
- ✅ Refactoring code structure (moving files, renaming modules)
- ✅ Changing architecture (new components, different flows)
- ✅ Making important decisions (ADRs in decisions.md)
- ✅ Adding/removing dependencies (update dependencies.md)
- ✅ Discovering bugs or solutions (update debugging.md)
- ✅ Establishing new patterns (update patterns.md)

**How to update:**
1. Identify which topic file(s) need updates
2. Edit the relevant `.claude/memory/*.md` file(s)
3. Update "Current Phase" section below if status changed
4. Commit memory changes with code changes

---

## Project Overview

- **Repo:** `knowledge-finder-bot`
- **Package:** `knowledge_finder_bot` (Python)
- **Purpose:** MS Teams/Telegram chatbot for NotebookLM queries via nlm-proxy
- **Stack:** Python 3.11+, uv, M365 Agents SDK, aiohttp, Pydantic

## Quick Reference

| Item | Value |
|------|-------|
| Package Manager | `uv` (not pip) |
| Run Commands | `uv run python -m knowledge_finder_bot.main` |
| Test Commands | `uv run pytest tests/ -v` |
| Tunnel Tool | devtunnel (`.\run_devtunnel.ps1`) |
| Local Testing | Agent Playground (`.\run_agentplayground.ps1`) |
| Local Port | 3978 |

## Topic Files

| File | Description |
|------|-------------|
| [project-structure.md](./project-structure.md) | Directory layout, key files |
| [dependencies.md](./dependencies.md) | Package dependencies, versions |
| [azure-config.md](./azure-config.md) | Azure Bot, AD, Graph API setup |
| [patterns.md](./patterns.md) | Code patterns, conventions |
| [debugging.md](./debugging.md) | Common issues, solutions |
| [decisions.md](./decisions.md) | Architecture decisions, rationale |

## Current Phase

- **Status:** ✅ Dual-mode response delivery (streaming + buffered) complete
- **Milestone:** Fixed non-streaming channels (emulator/Agent Playground) receiving buffered responses
- **Next:** Production deployment, Teams E2E testing
- **Tests:** All passing (90/90 tests)

**Recent Completion:**
- ✅ M365 Agents SDK migration (v0.7.0)
- ✅ Graph API client with app-only authentication (8/8 tests)
- ✅ ACL service with YAML-based access control (14/14 tests)
- ✅ Pydantic models with GUID validation (11/11 tests)
- ✅ Bot handler with ACL enforcement (10/10 tests)
- ✅ **Dual-mode routing**: Fake AAD IDs → MockGraphClient, real AAD IDs → Graph API
- ✅ MockGraphClient for Agent Playground testing without Azure AD
- ✅ **nlm-proxy integration**: OpenAI SDK client with streaming, multi-turn, formatting (26/26 tests)
  - NLMClient with streaming/non-streaming support (8/8 tests)
  - SessionStore for multi-turn conversations (6/6 tests)
  - Response formatter with source attribution (5/5 tests)
  - Bot integration with typing indicator + error handling (7/7 tests)

**Critical Feature - TEST_MODE:**
- Enable `TEST_MODE=true` for Agent Playground ACL testing
- Set `TEST_USER_GROUPS` to simulate AD group memberships (comma-separated GUIDs)
- Automatic routing: `00000000-0000-0000-0000-*` prefix → mock, real AAD ID → Graph API
- Both clients coexist - per-request routing based on AAD ID pattern
- Test groups defined in `config/acl.yaml` (Admin: 11111111..., HR: 22222222..., Eng: 33333333...)

**🔄 Update this section when:**
- Starting a new task
- Completing a major milestone
- Changing implementation approach

## Key Decisions

1. **M365 Agents SDK over Bot Framework** - Bot Framework SDK EOL Dec 31, 2025 (completed)
2. **uv over pip** - Faster, better dependency resolution, `[dependency-groups]` syntax
3. **devtunnel for development** - Microsoft-native tunneling, integrates with Azure
4. **Agent Playground for testing** - Official M365 tool, better than Bot Framework Emulator
5. **OpenAI SDK first** - Direct nlm-proxy integration, LangGraph later if needed
6. **App-only Graph API** - No user consent dialogs, simpler auth flow

See [decisions.md](./decisions.md) for full Architecture Decision Records (ADRs).

## Commands Cheatsheet

```bash
# Setup
uv sync

# Run bot
uv run python -m knowledge_finder_bot.main

# Run tests
uv run pytest tests/ -v

# Start devtunnel (saves endpoint to .devtunnel-endpoint)
.\run_devtunnel.ps1

# Test with Agent Playground (auto-detects devtunnel endpoint)
.\run_agentplayground.ps1

# Health check
curl http://localhost:3978/health
```

## Related Docs

- **Developer Guide:** `CLAUDE.md` (root) - Commands, architecture, components
- **Design:** `docs\plans\notebooklm-chatbot-design-v2-fixed.md`
- **Azure Setup:** `docs/plans/azure-app-registration-guide.md`
