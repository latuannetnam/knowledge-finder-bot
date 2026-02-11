# update-docs Plugin

Automatic documentation update system for the knowledge-finder-bot project.

> **Installation Required:** Run the installation script from the project root. See [Installation](#installation) below.

## Features

- Analyzes git changes (status, diff, commits)
- Classifies changes into 10 types (features, dependencies, env vars, etc.)
- Proposes documentation updates based on CLAUDE.md rules
- Safe approval workflow before editing files
- Optional auto-commit with conventional commit messages

## Usage

```
/update-knowledge-bot-docs                  # Analyze changes and propose updates
/update-knowledge-bot-docs --auto-commit    # Propose + auto-commit after approval
```

## Integration

Works with hookify rule `.claude/hookify.detect-completion.local.md` for proactive detection.

## Installation

**One-time installation per developer:**

```bash
# From project root (recommended)
./scripts/install-plugins.sh      # Linux/Mac
.\scripts\install-plugins.ps1     # Windows
```

The script will:
1. Register the project's local marketplace (`knowledge-finder-bot-plugins`)
2. Install the `update-docs` plugin via `claude plugin install`
3. Enable the plugin

**Verify installation:**

```bash
# Restart Claude Code, then:
/help | grep update-docs  # Should show the skill
```

**After pulling plugin updates from git:**

```bash
# Re-run installation script to update
./scripts/install-plugins.sh      # Linux/Mac
.\scripts\install-plugins.ps1     # Windows
```

**Note:** This plugin is distributed as a local marketplace in `.claude/plugins/` (git-tracked). The installation script registers it with Claude Code's plugin system for proper discovery.

## Author

knowledge-finder-bot team
