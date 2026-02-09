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
| Bot Endpoint | `https://knowledge-finder-bot.nport.io/api/messages` |
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

- **Status:** ✅ M365 Agents SDK migration complete and verified working
- **Milestone:** Echo bot functional with M365 Agents SDK v0.7.0 + Agent Playground tested
- **Next:** Implement nlm-proxy integration and Azure AD auth
- **Tests:** All passing (2/2 bot tests, working with Agent Playground)

**Recent Completion:**
- ✅ Migrated from Bot Framework SDK → M365 Agents SDK
- ✅ Fixed authentication using official Microsoft pattern
- ✅ Added `microsoft-agents-authentication-msal` package
- ✅ Verified working with Agent Playground

**Critical Discovery - Authentication Fix:**
- M365 Agents SDK requires specific env var format: `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*`
- Must use `MsalConnectionManager` from `microsoft-agents-authentication-msal`
- Must use `load_configuration_from_env()` to load SDK config
- Pattern from: [github.com/microsoft/Agents](https://github.com/microsoft/Agents)

**🔄 Update this section when:**
- Starting a new task
- Completing a major milestone
- Changing implementation approach

## Key Decisions

1. **M365 Agents SDK over Bot Framework** - Bot Framework SDK EOL Dec 31, 2025 (completed)
2. **uv over pip** - Faster, better dependency resolution, `[dependency-groups]` syntax
3. **Nport over ngrok** - Persistent subdomain for free (`knowledge-finder-bot.nport.io`)
4. **OpenAI SDK first** - Direct nlm-proxy integration, LangGraph later if needed
5. **App-only Graph API** - No user consent dialogs, simpler auth flow

See [decisions.md](./decisions.md) for full Architecture Decision Records (ADRs).

## Related Docs

- **Developer Guide:** `CLAUDE.md` (root) - Commands, architecture, components
- **Design:** `docs/plans/notebooklm-chatbot-design.md`
- **Azure Setup:** `docs/plans/azure-app-registration-guide.md`
