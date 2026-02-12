# Creating Local Claude Code Skills (Legacy Reference)

> **Note:** This document is preserved for reference. It describes the skill creation process for Claude Code.

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

Lists all plugins in the marketplace.

### 2. Plugin Manifest (`.claude/plugins/plugins/<plugin-name>/.claude-plugin/plugin.json`)

Describes the plugin.

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
...
```
