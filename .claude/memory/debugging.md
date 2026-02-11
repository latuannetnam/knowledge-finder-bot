# Debugging & Troubleshooting

## Common Issues

### Bot Not Responding

| Symptom | Cause | Solution |
|---------|-------|----------|
| No response in Agent Playground | Bot not running | `uv run python -m knowledge_finder_bot.main` |
| "Cannot connect" | Wrong port | Ensure port 3978, check `/health` endpoint |
| "Unauthorized" in Agent Playground | Wrong endpoint | Use `.\run_agentplayground.ps1` to auto-detect devtunnel endpoint |

### Devtunnel Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Exiting. Stop the existing host process..." | Tunnel already running from previous session | **This is CORRECT behavior** - tunnel is active. Check saved endpoint or stop existing process if restart needed |
| Script shows unnecessary re-authentication | Authentication check was failing (fixed in script) | Update `run_devtunnel.ps1` to latest version |
| Tunnel unreachable after inactivity | Stale connection (ghost process) | Script auto-detects and recreates tunnel. Run `.\run_devtunnel.ps1` |
| Don't see "Tunnel is now running..." message | Script exited early (found existing tunnel) | **Normal** - message only shows when starting NEW tunnel. Existing tunnel already working |
| `.devtunnel-endpoint` file missing | Endpoint capture failed or tunnel not started | Check `devtunnel list`, restart tunnel with `.\run_devtunnel.ps1` |

**Understanding Devtunnel Script Behavior:**

The `run_devtunnel.ps1` script has two execution paths:

1. **Existing Tunnel Found** (most common after first run):
   ```
   Checking if tunnel is already hosted...
   Active devtunnel host process found (PID: xxxxx)
   Saved endpoint: https://xxx.devtunnels.ms/api/messages
   Exiting. Stop the existing host process first if you need to restart.
   ```
   - ✅ This means your tunnel is **already working**
   - ✅ Endpoint is saved in `.devtunnel-endpoint`
   - ✅ No action needed - use the existing tunnel

2. **New Tunnel Started**:
   ```
   Starting tunnel host...
   Hosting port: 3978
   Connect via browser: https://xxx.devtunnels.ms
   Bot Endpoint: https://xxx.devtunnels.ms/api/messages
   Tunnel is now running. Press Ctrl+C to stop.
   ```
   - ✅ Fresh tunnel created
   - ✅ Script stays running to keep tunnel alive

**When to Force Restart Devtunnel:**

Only restart if you experience actual connectivity issues:

```powershell
# Stop existing tunnel
Get-Process devtunnel | Stop-Process

# Start fresh tunnel
.\run_devtunnel.ps1
```

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

# Show tunnel status (check if it's running)
devtunnel show knowledge-finder-bot

# Check for running devtunnel processes
Get-Process devtunnel  # PowerShell
ps aux | grep devtunnel  # Unix

# Check devtunnel authentication
devtunnel user show

# Force stop devtunnel
Get-Process devtunnel | Stop-Process  # PowerShell
pkill devtunnel  # Unix

# Verbose pytest
uv run pytest tests/ -v --tb=long
```

## Devtunnel Diagnostics

**Check if tunnel is actually working:**

```powershell
# 1. Verify tunnel process is running
Get-Process devtunnel

# 2. Check tunnel status
devtunnel show knowledge-finder-bot

# 3. Verify saved endpoint exists
Get-Content .devtunnel-endpoint

# 4. Test endpoint connectivity (requires bot server running)
curl (Get-Content .devtunnel-endpoint).Replace('/api/messages', '/health')
```

**Expected healthy output:**
- Process: `devtunnel` with PID shown
- Status: `hostConnections: 1` or more
- Endpoint file: Contains `https://xxx.devtunnels.ms/api/messages`
- Health check: `{"status": "ok"}` with HTTP 200

## Logging

Logs use structlog with ISO timestamps. Check terminal for:
- `starting_bot_server` - Server started
- `message_received` - User sent message
- `Error processing activity` - Something went wrong
