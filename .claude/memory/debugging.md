# Debugging & Troubleshooting

## Common Issues

### Bot Not Responding

| Symptom | Cause | Solution |
|---------|-------|----------|
| No response in Agent Playground | Bot not running | `uv run python -m knowledge_finder_bot.main` |
| "Cannot connect" | Wrong port | Ensure port 3978, check `/health` endpoint |
| "Unauthorized" in Agent Playground | Wrong endpoint | Use `.\run_agentplayground.ps1` to auto-detect devtunnel endpoint |

### Teams Integration Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "401 Unauthorized" | Wrong credentials | Verify `MICROSOFT_APP_ID` matches Azure Portal |
| "502 Bad Gateway" | Bot crashed | Check terminal for Python errors |
| No messages received | Tunnel not running | Run `.\run_devtunnel.ps1` |
| URL not reachable | devtunnel disconnected | Restart devtunnel, check `.devtunnel-endpoint` file |

### Dependency Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Module not found | Deps not installed | Run `uv sync` |
| Import error | Wrong Python | Ensure Python 3.11+, use `uv run` |
| Package conflict | Version mismatch | Delete `.venv`, run `uv sync` |

## Debug Commands

```bash
# Check health
curl http://localhost:3978/health

# Check if port is in use
netstat -an | findstr 3978  # Windows
lsof -i :3978               # Unix

# Check devtunnel endpoint
Get-Content .devtunnel-endpoint  # PowerShell
type .devtunnel-endpoint         # CMD

# List devtunnels
devtunnel list

# Show tunnel status
devtunnel show knowledge-finder-bot

# Verbose pytest
uv run pytest tests/ -v --tb=long
```

## Logging

Logs use structlog with ISO timestamps. Check terminal for:
- `starting_bot_server` - Server started
- `message_received` - User sent message
- `Error processing activity` - Something went wrong
