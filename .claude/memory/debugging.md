# Debugging & Troubleshooting

## Common Issues

### Bot Not Responding

| Symptom | Cause | Solution |
|---------|-------|----------|
| No response in Emulator | Bot not running | `uv run python -m knowledge_finder_bot.main` |
| "Cannot connect" | Wrong port | Ensure port 3978, check `/health` endpoint |
| "Unauthorized" in Emulator | App ID set | Leave App ID/Password empty for local testing |

### Teams Integration Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "401 Unauthorized" | Wrong credentials | Verify `MICROSOFT_APP_ID` matches Azure Portal |
| "502 Bad Gateway" | Bot crashed | Check terminal for Python errors |
| No messages received | Tunnel not running | Start `nport 3978 -s knowledge-finder-bot` |
| URL not reachable | Nport disconnected | Restart Nport tunnel |

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

# Test Nport tunnel
curl https://knowledge-finder-bot.nport.io/health

# Verbose pytest
uv run pytest tests/ -v --tb=long
```

## Logging

Logs use structlog with ISO timestamps. Check terminal for:
- `starting_bot_server` - Server started
- `message_received` - User sent message
- `Error processing activity` - Something went wrong
