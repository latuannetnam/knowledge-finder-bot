# NotebookLM Chatbot

MS Teams and Telegram chatbot for querying NotebookLM notebooks via nlm-proxy.

## Status

**Current:** Echo bot implementation (Phase 1)

## Quick Start

### Prerequisites

- Python 3.11+
- Azure Bot registration (for Teams deployment)
- Bot Framework Emulator (for local testing)

### Development Setup

**Windows:**
```powershell
.\scripts\dev-setup.ps1
```

**Unix/Mac:**
```bash
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh
```

### Running Locally

1. Edit `.env` with your Azure Bot credentials
2. Start the bot:
   ```bash
   python -m knowledge_finder_bot.main
   ```
3. Open Bot Framework Emulator
4. Connect to `http://localhost:3978/api/messages`

### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
nlm-chatbot/
├── src/knowledge_finder_bot/
│   ├── __init__.py
│   ├── config.py          # Pydantic settings
│   ├── main.py            # Application entrypoint
│   └── bot/
│       ├── __init__.py
│       └── bot.py         # Bot implementation
├── tests/
│   ├── conftest.py        # Test fixtures
│   ├── test_config.py     # Config tests
│   └── test_bot.py        # Bot tests
├── scripts/
│   ├── dev-setup.ps1      # Windows setup
│   └── dev-setup.sh       # Unix setup
├── pyproject.toml
├── .env.example
└── README.md
```

## License

MIT
