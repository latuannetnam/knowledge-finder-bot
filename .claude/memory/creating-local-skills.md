# Creating Local Claude Code Skills

## Overview

This guide documents how to create project-specific skills that are shared via git and installed through Claude Code's plugin system.

## Architecture: 3-Layer System

Claude Code uses a **marketplace-based plugin system** with three layers:

```
Marketplace (local or remote)
  └── Plugin (contains metadata + resources)
      └── Skill (markdown-based workflow)
```

**Key insight:** You cannot just copy files to `~/.claude/plugins/` — plugins must be registered through the marketplace system.

## Project Structure

```
.claude/plugins/                                    # Local marketplace root
├── .claude-plugin/
│   └── marketplace.json                            # Marketplace manifest
└── plugins/
    └── <plugin-name>/                              # Individual plugin
        ├── .claude-plugin/
        │   └── plugin.json                         # Plugin manifest
        ├── README.md                               # Plugin documentation
        └── skills/
            └── <skill-name>/                       # Skill directory
                └── SKILL.md                        # Skill content
```

## File Requirements

### 1. Marketplace Manifest (`.claude/plugins/.claude-plugin/marketplace.json`)

Lists all plugins in the marketplace:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "knowledge-finder-bot-plugins",
  "description": "Custom Claude Code plugins for the knowledge-finder-bot project",
  "owner": {
    "name": "knowledge-finder-bot team",
    "email": "latuannetnam@gmail.com"
  },
  "plugins": [
    {
      "name": "update-docs",
      "description": "Automatic documentation update system",
      "version": "1.0.0",
      "author": {
        "name": "knowledge-finder-bot team",
        "email": "latuannetnam@gmail.com"
      },
      "source": "./plugins/update-docs",
      "category": "productivity"
    }
  ]
}
```

**Key fields:**
- `name`: Marketplace ID (used in `@marketplace-name`)
- `plugins[].source`: Relative path to plugin directory
- `plugins[].category`: One of: development, productivity, testing, security, learning, etc.

### 2. Plugin Manifest (`.claude/plugins/plugins/<plugin-name>/.claude-plugin/plugin.json`)

Describes the plugin:

```json
{
  "name": "update-docs",
  "version": "1.0.0",
  "description": "Automatic documentation update system for knowledge-finder-bot",
  "author": {
    "name": "knowledge-finder-bot team",
    "email": "latuannetnam@gmail.com"
  }
}
```

**Minimal required fields:** `name`, `version`, `description`, `author`

### 3. Skill File (`.claude/plugins/plugins/<plugin-name>/skills/<skill-name>/SKILL.md`)

**Critical requirements:**

1. **Must be named `SKILL.md`** (not `<skill-name>.md`)
2. **Must be in a subdirectory** (`skills/<skill-name>/SKILL.md`, not `skills/<skill-name>.md`)
3. **Frontmatter uses YAML**, only `name` and `description` required:

```markdown
---
name: update-docs
description: Analyze code changes and propose documentation updates
---

# Documentation Update Assistant

This skill analyzes recent code changes and proposes documentation updates.

## Step 1: Detect Changes

### Git Status
```bash
git status --short
```

...
```

**Do NOT include** `version`, `allowed-tools`, or other fields in frontmatter — they're ignored.

## Installation Workflow

### For Team Members

**1. Clone the repository:**
```bash
git clone <repo-url>
cd knowledge-finder-bot
```

**2. Run installation script:**
```bash
./scripts/install-plugins.sh      # Linux/Mac
.\scripts\install-plugins.ps1     # Windows
```

The script performs:
1. `claude plugin marketplace add ./.claude/plugins` — Register local marketplace
2. `claude plugin install update-docs@knowledge-finder-bot-plugins --scope user` — Install plugin
3. `claude plugin enable update-docs@knowledge-finder-bot-plugins` — Enable plugin

**3. Restart Claude Code:**
```bash
/exit
cc
```

**4. Verify:**
```bash
/help | grep update-docs
/update-docs
```

### After Pulling Updates

Re-run the installation script to update:
```bash
./scripts/install-plugins.sh      # Linux/Mac
.\scripts\install-plugins.ps1     # Windows
```

## Manual Installation (Understanding the Process)

If you need to install manually:

```bash
# Step 1: Register marketplace
claude plugin marketplace add "./.claude/plugins"

# Step 2: Install plugin
claude plugin install update-docs@knowledge-finder-bot-plugins --scope user

# Step 3: Enable plugin
claude plugin enable update-docs@knowledge-finder-bot-plugins

# Step 4: Restart Claude Code
/exit
cc
```

## Validation

Validate your plugin structure before committing:

```bash
# Validate plugin
claude plugin validate .claude/plugins/plugins/update-docs

# Expected: ✔ Validation passed
```

## Common Issues

### Issue: "Plugin not found in any configured marketplace"

**Cause:** Marketplace not registered, or plugin not listed in `marketplace.json`

**Fix:**
1. Verify `.claude/plugins/.claude-plugin/marketplace.json` exists
2. Check `plugins` array includes your plugin
3. Run `claude plugin marketplace add ./.claude/plugins`

### Issue: "/help doesn't show my skill"

**Cause:** Incorrect file structure or naming

**Fix:**
1. Skill file must be `SKILL.md` (not `<skill-name>.md`)
2. Must be in subdirectory: `skills/<skill-name>/SKILL.md`
3. Plugin must be enabled in `~/.claude/settings.json`

### Issue: "Skill appears but doesn't work"

**Cause:** Invalid YAML frontmatter or missing required fields

**Fix:**
1. Frontmatter must have `name` and `description`
2. Use `---` delimiters (not `===`)
3. No extra fields like `version` or `allowed-tools`

## Team Sharing Workflow

### 1. Development
- Edit `.claude/plugins/plugins/update-docs/skills/update-docs/SKILL.md`
- Test locally (re-run installation script)
- Commit changes to git

### 2. Distribution
- Team members pull latest changes
- Re-run installation script
- Restart Claude Code

### 3. Versioning
- Update `version` in `.claude/plugins/plugins/update-docs/.claude-plugin/plugin.json`
- Update `version` in `.claude/plugins/.claude-plugin/marketplace.json`
- Document changes in plugin's README.md

## Advanced: Multiple Skills in One Plugin

A plugin can contain multiple skills:

```
.claude/plugins/plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    ├── skill-one/
    │   └── SKILL.md
    ├── skill-two/
    │   └── SKILL.md
    └── skill-three/
        └── SKILL.md
```

Each skill will appear as a separate command: `/skill-one`, `/skill-two`, `/skill-three`

## Reference: Working Example

See this project's `update-docs` plugin:
- Marketplace: `.claude/plugins/.claude-plugin/marketplace.json`
- Plugin: `.claude/plugins/plugins/update-docs/.claude-plugin/plugin.json`
- Skill: `.claude/plugins/plugins/update-docs/skills/update-docs/SKILL.md`
- Install script: `scripts/install-plugins.sh` / `scripts/install-plugins.ps1`

## External Resources

- [Claude Code Plugins Official Marketplace](https://github.com/anthropics/claude-plugins-official)
- [Superpowers Plugin Example](https://github.com/obra/superpowers) (remote marketplace)
- [Plugin Development Guide](https://docs.anthropic.com/en/docs/claude-code/plugins) (official docs)
