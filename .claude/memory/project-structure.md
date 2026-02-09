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
│       │   └── bot.py       # NotebookLMBot (ActivityHandler)
│       ├── auth/            # Azure AD, Graph API
│       ├── acl/             # Access control (group → notebooks)
│       ├── nlm/             # nlm-proxy client
│       └── channels/        # Teams/Telegram formatters
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   └── test_bot.py
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
| `src/knowledge_finder_bot/main.py` | Server entrypoint, routes |
| `src/knowledge_finder_bot/bot/bot.py` | Bot message handler |
| `src/knowledge_finder_bot/config.py` | Environment configuration |
| `pyproject.toml` | Dependencies, build config |
| `.env` | Local secrets (not in git) |
