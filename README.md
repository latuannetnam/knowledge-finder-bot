# Knowledge Finder Bot

**A Microsoft Teams & Telegram chatbot that answers questions using Google's NotebookLM.**

[![Status](https://img.shields.io/badge/Status-Migration_Complete-success)](./docs/architecture.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](./pyproject.toml)

This bot allows users to query curated knowledge bases (NotebookLM notebooks) directly from their chat interface. It handles authentication, access control via Azure AD groups, and routes queries to the appropriate notebook.

## 🚀 Quick Links

- **[Setup Guide](./docs/setup.md)** - Installation and local development.
- **[Architecture](./docs/architecture.md)** - System design and components.
- **[Contributing](./docs/contributing.md)** - Coding standards and testing.
- **[Deployment](./docs/deployment.md)** - Azure configuration and hosting.

## ⚡ Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Run the bot
uv run python -m knowledge_finder_bot.main

# 3. Run tests
uv run pytest tests/ -v
```

## Project Status

**Current Phase: M365 Agents SDK Migration (Completed)**
The bot has been successfully migrated to the new Microsoft 365 Agents SDK and is currently functioning as an **Echo Bot**. The core infrastructure (auth, config, logging) is in place.

**Next Steps:**
- Implement `nlm-proxy` integration.
- Implement Azure AD Group ACLs.

## Repository Structure

```
knowledge-finder-bot/
├── docs/                   # Documentation
├── src/                    # Source code
│   └── knowledge_finder_bot/
│       ├── bot/            # Bot logic (Agents SDK)
│       ├── config.py       # Configuration
│       └── main.py         # Entry point
├── tests/                  # Unit tests
├── scripts/                # Utility scripts
├── pyproject.toml          # Dependencies (uv)
└── README.md               # This file
```

## License

MIT
