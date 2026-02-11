# Auto-Documentation Update System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a dual-trigger documentation update system that proactively reminds developers to update Just-in-Time docs after completing tasks, using hookify detection + manual `/update-docs` skill.

**Architecture:** Two-phase approach - (1) standalone `/update-docs` skill that analyzes git changes and proposes doc updates, (2) hookify rule that detects task completion keywords and suggests running the skill. Smart detection combines git diff (what changed) with conversation context (why it changed).

**Tech Stack:** Claude Code skills (Markdown + YAML), hookify plugin, git CLI, Edit/Read/Bash tools

---

## Context

**Why this is needed:**
The knowledge-finder-bot project has comprehensive Just-in-Time documentation in `.claude/memory/` and `CLAUDE.md`, but keeping it updated requires manual effort. Developers often forget to update docs after completing features, leading to drift between code and documentation.

**Current state:**
- Manual update checklist in `CLAUDE.md` (lines 27-36) mapping change types to doc files
- Modular memory system: `MEMORY.md`, `dependencies.md`, `patterns.md`, `debugging.md`, `decisions.md`, `project-structure.md`, `azure-config.md`
- No automation - relies on developer discipline

**Desired outcome:**
- Proactive reminders to update docs when tasks complete (via hookify)
- Manual `/update-docs` skill for on-demand updates
- Smart change detection using git diff + conversation context
- Safe workflow: propose updates → user approves → edit files → optional commit

---

## Architecture Overview

```
Task Completion → Hookify Rule Detects → Suggests /update-docs
                                                ↓
User Invokes → /update-docs Skill
  ↓                    ↓
  ├── 1. Git Analysis (status, diff, log)
  ├── 2. Classify Changes (new feature, dependencies, env vars, etc.)
  ├── 3. Map to Doc Files (using CLAUDE.md table)
  ├── 4. Propose Updates (checklist format)
  ├── 5. Get User Approval
  ├── 6. Execute Edits (Edit tool)
  └── 7. Optional Commit (with --auto-commit flag)
```

---

## Task 1: Create Project-Level Plugin Structure (Test Discovery)

**Files:**
- Create: `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\plugins\update-docs\.claude-plugin\plugin.json`
- Create: `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\plugins\update-docs\README.md`
- Create: `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\plugins\update-docs\commands\update-docs.md`

**Step 1: Create plugin directory structure**

```bash
mkdir -p .claude/plugins/update-docs/.claude-plugin
mkdir -p .claude/plugins/update-docs/commands
```

**Step 2: Create plugin.json metadata**

Create `.claude/plugins/update-docs/.claude-plugin/plugin.json`:

```json
{
  "name": "update-docs",
  "version": "1.0.0",
  "description": "Automatic documentation update system for knowledge-finder-bot",
  "author": {
    "name": "knowledge-finder-bot team",
    "email": "noreply@example.com"
  }
}
```

**Step 3: Create plugin README**

Create `.claude/plugins/update-docs/README.md`:

```markdown
# update-docs Plugin

Automatic documentation update system for the knowledge-finder-bot project.

## Features

- Analyzes git changes (status, diff, commits)
- Classifies changes into 8 types (features, dependencies, env vars, etc.)
- Proposes documentation updates based on CLAUDE.md rules
- Safe approval workflow before editing files
- Optional auto-commit with conventional commit messages

## Usage

```
/update-docs                  # Analyze changes and propose updates
/update-docs --auto-commit    # Propose + auto-commit after approval
```

## Integration

Works with hookify rule `.claude/hookify.detect-completion.local.md` for proactive detection.

## Author

knowledge-finder-bot team
```

**Step 4: Create skill file with YAML frontmatter**

Create `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
---
name: update-docs
description: Analyze code changes and propose documentation updates
version: 1.0.0
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Edit
---

# Documentation Update Assistant

This skill analyzes recent code changes and proposes documentation updates based on the project's update rules.

## Step 1: Detect Changes

### Git Status
!`git status --short`

### Changed Files
!`git diff HEAD --name-status`

### Recent Commit
!`git log -1 --pretty=format:"%h %s%n%b"`

### Dependency Changes
!`git diff HEAD -- pyproject.toml | grep -E "^[+-]" | head -20`

### Load Update Rules
!`cat CLAUDE.md | sed -n '27,36p'`

### Load Current Phase
!`cat .claude/memory/MEMORY.md | sed -n '53,80p'`
```

**Step 5: Test project-level plugin discovery**

Run: Restart Claude Code session in project directory

In chat: `/help | grep update-docs`

Expected: Skill should appear in help output

**Step 6: Test basic invocation**

In chat: `/update-docs`

Expected: Skill should load and show git context

**Step 7: Document discovery results**

**If plugin is discovered ✅:**
- Continue with this structure
- All team members get plugin via git
- Document in README.md

**If plugin is NOT discovered ❌:**
- Execute fallback (see Task 1B below)

---

## Task 1B: Fallback to User-Level Plugin (If Discovery Fails)

**Execute this ONLY if Step 7 shows plugin is NOT discovered**

**Step 1: Move plugin to user-level directory**

```bash
cp -r .claude/plugins/update-docs ~/.claude/plugins/
```

**Step 2: Update installation docs**

Add to `docs/setup.md`:

```markdown
## Install update-docs Plugin

This project includes a custom `/update-docs` skill for automatic documentation updates.

**Installation:**

```bash
# From project root
cp -r .claude/plugins/update-docs ~/.claude/plugins/
```

**Verify installation:**

```bash
cc  # Start Claude Code
/help | grep update-docs  # Should show the skill
```
```

**Step 3: Keep project structure for reference**

Leave `.claude/plugins/update-docs/` in git as reference/template.

Add note to `.claude/plugins/update-docs/README.md`:

```markdown
> **Note:** Claude Code doesn't currently auto-discover project-level plugins.
> Install to `~/.claude/plugins/` using instructions in `docs/setup.md`.
```

**Step 4: Test user-level installation**

Run: `/help | grep update-docs`

Expected: Skill should now appear

---

## Task 2: Implement Change Classification Logic

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md` (or `~/.claude/plugins/update-docs/commands/update-docs.md` if using fallback)

**Step 1: Add classification instructions to skill**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
## Step 2: Classify Change Types

Based on git output, identify which change types occurred:

**1. New Feature/Module**
Detection: New files matching `src/knowledge_finder_bot/*/` or `tests/test_*.py`
Map to:
- `README.md` (Features list, Repository Structure, Project Status)
- `docs/architecture.md` (System components)
- `CLAUDE.md` (Key Components section)
- `.claude/memory/project-structure.md`
- `.claude/memory/MEMORY.md` (Current Phase)

**2. Dependencies**
Detection: Changes to `pyproject.toml`
Map to:
- `README.md` (Prerequisites section if major dependency)
- `docs/setup.md` (Prerequisites, installation steps)
- `.claude/memory/dependencies.md`

**3. Environment Variables**
Detection: Changes to `.env.example` OR `config.py` with new Field definitions
Map to:
- `README.md` (Environment Variables section)
- `docs/setup.md` (Configuration section)
- `CLAUDE.md` (if critical)
- `.env.example`

**4. Code Patterns**
Detection: New logging patterns, decorators, reusable utilities
Map to:
- `.claude/memory/patterns.md`
- `docs/contributing.md` (if coding standard established)

**5. Bug Fixes/Solutions**
Detection: Commits with `fix:` prefix OR error handling improvements
Map to:
- `.claude/memory/debugging.md`
- `README.md` (if fixes known issue in status)

**6. Architecture Changes**
Detection: 2+ core files modified (main.py, bot/bot.py, auth/, acl/, nlm/)
Map to:
- `README.md` (Architecture diagram, Repository Structure)
- `docs/architecture.md` (System design)
- `CLAUDE.md` (Architecture section)

**7. Development Tools**
Detection: Changes to `*.ps1` scripts OR `scripts/` directory
Map to:
- `README.md` (Quick Start commands)
- `docs/setup.md` (Development workflow)
- `.claude/memory/MEMORY.md` (Quick Reference)

**8. Important Decisions**
Detection: Major design choices, ADRs
Map to:
- `.claude/memory/decisions.md`
- `docs/architecture.md` (if architectural decision)

**9. Test Results/Coverage** (NEW)
Detection: Test output showing passed/failed tests OR coverage changes
Map to:
- `README.md` (Status badges, Test Results section)
- `.claude/memory/MEMORY.md` (Current Phase - test count)

**10. Deployment Changes** (NEW)
Detection: Changes to deployment scripts, Docker, CI/CD
Map to:
- `README.md` (if deployment method changes)
- `docs/deployment.md`

## Your Classification Task

Analyze the git output above and list which change types apply.
For each change type detected, list the specific documentation files that need updating.
```

**Step 2: Test classification with sample changes**

Create test file:
```bash
echo "# Test" > src/knowledge_finder_bot/test_module.py
git add src/knowledge_finder_bot/test_module.py
```

Run: `/update-docs`

Expected: Should detect "New Feature: test_module" and suggest updating project-structure.md, CLAUDE.md, MEMORY.md

**Step 3: Clean up test changes**

Run: `git reset HEAD src/knowledge_finder_bot/test_module.py && rm src/knowledge_finder_bot/test_module.py`

---

## Task 3: Implement Update Proposal Generation

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add proposal formatting instructions**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
## Step 3: Generate Update Proposals

For each detected change type, create a checklist entry in this format:

```
🔍 Detected Changes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [Change Type]: [Specific item]
   Files changed:
   - [file path] ([status: new/modified])

   📝 Documentation to update:
   ✓ [doc file 1] ([what to add/update])
   ✓ [doc file 2] ([what to add/update])

2. [Next change type]...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Example Output

For a new feature with dependency:

```
🔍 Detected Changes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. New Feature: streaming support
   Files changed:
   - src/knowledge_finder_bot/nlm/client.py (new)
   - tests/test_nlm_streaming.py (new)

   📝 Documentation to update:
   ✓ docs/architecture.md (add NLM streaming component)
   ✓ CLAUDE.md (add to Key Components table)
   ✓ .claude/memory/project-structure.md (document nlm/ directory)
   ✓ .claude/memory/MEMORY.md (update Current Phase to "✅ Streaming complete")

2. Dependencies: Added openai>=1.59.0
   Files changed:
   - pyproject.toml

   📝 Documentation to update:
   ✓ .claude/memory/dependencies.md (add openai SDK details)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Proceed with these updates? (yes/no/selective)
```

## Your Task

Present the proposals in the format above, then wait for user response.
```

**Step 2: Test proposal generation**

Create realistic test scenario:
```bash
echo "openai>=1.59.0" >> pyproject.toml
git add pyproject.toml
```

Run: `/update-docs`

Expected: Should show formatted proposal with dependency change detected

**Step 3: Revert test changes**

Run: `git checkout pyproject.toml`

---

## Task 4: Implement Approval Workflow

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add approval handling instructions**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
## Step 4: Handle User Approval

**If user responds "yes" or "approve":**
- Proceed to Step 5 (execute all proposed updates)

**If user responds "selective":**
- Ask which specific files to update
- Only proceed with user-selected files

**If user responds "no" or "cancel":**
- Abort and show: "✅ Documentation update cancelled. No changes made."

**If no changes detected (git status clean):**
- Show improved message:
```
ℹ️ No uncommitted changes detected.

**Recent commits:**
- [hash] [subject] ([time] ago)
- [hash] [subject] ([time] ago)

Documentation appears synchronized with latest commit.
```
- Do not proceed to update steps

## Step 4B: Error Handling

**Handle common error scenarios gracefully:**

**If git commands fail:**
```
⚠️ Git error: [error message]

Possible causes:
- Not in a git repository
- Detached HEAD state
- Corrupted git index

Please ensure you're in a valid git repository and try again.
```
Abort gracefully, do not proceed with updates.

**If documentation file not found:**
```
⚠️ Documentation file not found: [file path]

Options:
1. Skip this file and continue with others
2. Create the file with template content
3. Abort entire update

What would you like to do? (skip/create/abort)
```

**If Edit tool fails on a file:**
```
❌ Failed to update [file]: [error message]

Possible causes:
- File was modified by another process
- Insufficient permissions
- Invalid old_string (content changed since detection)

Continuing with remaining files...
```
Continue updating other files, list all failures at end.

**If multiple files fail:**
```
⚠️ Update partially completed:

✅ Successfully updated:
- .claude/memory/MEMORY.md
- .claude/memory/dependencies.md

❌ Failed to update:
- README.md (content mismatch)
- docs/architecture.md (file locked)

Rollback changes? (yes/no)
```

Offer rollback option if any failures occurred.
```

**Step 2: Test error handling**

Test scenarios:
```bash
# Test 1: Not in git repo
cd /tmp
/update-docs
# Expected: Git error message, graceful abort

# Test 2: Missing doc file
cd D:\latuan\Programming\AIAgent\knowledge-finder-bot
rm .claude/memory/debugging.md
/update-docs
# Expected: File not found, offer skip/create/abort

# Test 3: No changes
git status  # Ensure clean
/update-docs
# Expected: Improved "no changes" message with recent commits
```

---

## Task 5: Implement MEMORY.md Current Phase Updates

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add MEMORY.md update template**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
## Step 5: Execute Documentation Updates

For each approved file, use the Read and Edit tools:

### Template: Update MEMORY.md Current Phase

**Read current content:**
```bash
!`cat .claude/memory/MEMORY.md`
```

**Generate new Current Phase section:**

```markdown
## Current Phase

- **Status:** ✅ [milestone from commit message] complete
- **Milestone:** [description of what was implemented]
- **Next:** [suggest logical next steps]
- **Tests:** All passing ([X/X] tests from git log or conversation)

**Recent Completion:**
- ✅ [milestone]
  - [feature/change 1]
  - [feature/change 2]
```

**Instructions for updating:**
1. Extract milestone from git commit subject line
2. Extract feature details from commit body
3. Look for test count in conversation or git commit message (e.g., "90/90 tests passing")
4. Use Edit tool to replace old Current Phase section with new one
5. Use exact old_string (entire old section) and new_string (entire new section)

**After editing:**
- Read .claude/memory/MEMORY.md again to verify update applied correctly
- Show user the updated section
- Track this file in successfully_updated list

## Step 5B: Rollback Strategy

**If any update fails after partial completion:**

1. **Track all operations:**
```python
successfully_updated = []  # Files that were edited successfully
failed_updates = []         # Files that failed to update
```

2. **On failure, present status:**
```
⚠️ Update partially completed:

✅ Successfully updated ([X] files):
- .claude/memory/MEMORY.md
- .claude/memory/dependencies.md

❌ Failed to update ([Y] files):
- README.md (reason: content mismatch)
- docs/architecture.md (reason: file locked)

Would you like to rollback the [X] successful changes? (yes/no)
```

3. **If user chooses "yes" to rollback:**
```bash
# Revert only the successfully updated files
git checkout [file1] [file2] [file3]
```

Show confirmation:
```
✅ Rolled back [X] files:
- .claude/memory/MEMORY.md
- .claude/memory/dependencies.md

All changes reverted. You can fix the issues and try again.
```

4. **If user chooses "no" (keep partial updates):**
```
⚠️ Keeping partial updates. You'll need to manually update:
- README.md
- docs/architecture.md

Failed files are listed above with reasons. Fix and re-run /update-docs.
```

5. **Exit gracefully:**
- Do NOT proceed to auto-commit if any failures occurred
- Show summary of what needs manual attention
```

**Step 2: Test MEMORY.md update**

Create realistic commit:
```bash
git commit --allow-empty -m "feat(nlm): add streaming support

- Implement AsyncOpenAI client
- Add session store
- 90/90 tests passing"
```

Run: `/update-docs`, approve, verify MEMORY.md Current Phase updates correctly

**Step 3: Revert test commit**

Run: `git reset HEAD~1`

---

## Task 6: Implement dependencies.md Updates

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add dependencies.md update template**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
### Template: Update dependencies.md

**When pyproject.toml changes are detected:**

1. **Extract new package from git diff:**
```bash
!`git diff HEAD -- pyproject.toml | grep "^+" | grep -v "^+++"`
```

2. **Find where package is used:**
```bash
!`grep -r "import [package-name]" src/knowledge_finder_bot/ | head -5`
```

3. **Generate dependency entry:**

```markdown
**[package-name]** - [purpose from code analysis]
- Used in: `[file paths from grep results]`
- Version: [version spec from pyproject.toml]
- Features: [key features based on imports/usage]
```

4. **Apply edit:**
- Read current .claude/memory/dependencies.md
- Find appropriate section (alphabetical or by category)
- Use Edit tool to insert new entry
- Verify by reading file again

**Example entry:**

```markdown
**openai** - OpenAI Python SDK for nlm-proxy integration
- Used in: `nlm/client.py`
- Version: >=1.59.0 (installed v2.18.0)
- Features: AsyncOpenAI, streaming responses, SSE buffering, extra_body metadata
```
```

**Step 2: Test dependencies.md update**

Add test dependency:
```bash
uv add pytest-asyncio  # If not already installed
```

Run: `/update-docs`, approve, verify dependencies.md gets new entry

**Step 3: Clean up**

Remove test dependency if it was just for testing

---

## Task 7: Implement project-structure.md Updates

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add project-structure.md update template**

Append to `update-docs.md`:

```markdown
### Template: Update project-structure.md

**When new module/directory is detected:**

1. **Identify new directory:**
```bash
!`git status --short | grep "^A" | grep "src/knowledge_finder_bot/"`
```

2. **Extract module purpose from code:**
- Read the new module's `__init__.py` or main file
- Look for module-level docstring
- Analyze imports and class/function names

3. **Generate directory entry:**

Add to the directory tree in project-structure.md:

```markdown
├── src/
│   └── knowledge_finder_bot/
│       ├── [new_module]/        # ✅ [PURPOSE] (IMPLEMENTED)
│       │   ├── __init__.py
│       │   └── [file].py        # [description]
```

4. **Update Key Files table if applicable:**

```markdown
| `src/knowledge_finder_bot/[module]/[file].py` | [Purpose from docstring] |
```

5. **Apply edit:**
- Read current project-structure.md
- Find the directory tree section
- Use Edit tool to insert new lines in alphabetical order
- Verify by reading file again
```

**Step 2: Test project-structure.md update**

Create test module:
```bash
mkdir -p src/knowledge_finder_bot/test_module
echo '"""Test module for documentation."""' > src/knowledge_finder_bot/test_module/__init__.py
git add src/knowledge_finder_bot/test_module
```

Run: `/update-docs`, approve, verify project-structure.md updates

**Step 3: Clean up test module**

Run: `git reset HEAD src/knowledge_finder_bot/test_module && rm -rf src/knowledge_finder_bot/test_module`

---

## Task 7B: Implement README.md Updates

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add README.md update templates**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
### Template: Update README.md

**README.md has multiple sections that may need updates:**

**1. Update Features List (lines 12-23)**

When new feature detected:
```markdown
- ✅ **[Feature Name]** - [Brief description]
```

Add to appropriate position in features list, maintaining ✅ prefix for completed features.

**2. Update Status Badges (lines 5-8)**

When test count changes:
```markdown
[![Tests](https://img.shields.io/badge/Tests-[X]%2F[X]_passing-brightgreen)](./tests/)
[![Coverage](https://img.shields.io/badge/Coverage-[Y]%25-green)](./tests/)
```

Extract test count from git commit or conversation (e.g., "90/90 tests passing" → `90%2F90`).

**3. Update Repository Structure (lines 84-124)**

When new module added:
```markdown
├── src/
│   └── knowledge_finder_bot/
│       ├── [new_module]/        # ✅ [PURPOSE] (IMPLEMENTED)
│       │   ├── __init__.py
│       │   └── [file].py        # [description]
```

**4. Update Test Results Section (lines 197-207)**

When test count changes:
```markdown
**Test Results:** [X]/[X] tests passing (100% success rate)
- [Module]: [X]/[X] ([Y]% coverage)
```

**5. Update Project Status (lines 216-243)**

When milestone completed:
```markdown
**[Feature Name]** (branch `feature/[name]`)
- Component with description
- Key features as bullet points
- **Total: [X]/[X] tests passing, [Y]% coverage**
```

**6. Update Architecture Diagram (lines 55-81)**

When architecture changes:
```
User (Teams) → Azure Bot Service → Bot Backend (aiohttp:3978)
                                          ↓
                        ┌──── [New Component] ────┐
                        │ [Description]           │
                        └─────────┬───────────────┘
```

**7. Update Environment Variables Section (lines 251-287)**

When new env var added:
```markdown
# [Category]
[VAR_NAME]=[default-value]  # [Description]
```

**Application instructions:**

For each README.md update:
1. Read current README.md
2. Identify the exact section to update (use line numbers as reference)
3. Use Edit tool with precise old_string/new_string
4. Verify update by reading the section again
5. Show user the diff

**Error handling:**
- If line numbers have shifted (file was edited elsewhere), search for section headers instead
- If section not found, warn user and skip that update
```

**Step 2: Test README.md updates**

Create test scenario:
```bash
# Add new feature with test count
git commit --allow-empty -m "feat(test): add test feature

- New module: test_feature
- 95/95 tests passing (was 90/90)"
```

Run: `/update-docs`, approve

Expected: Should propose updates to:
- Features list (add "✅ Test Feature")
- Status badges (90/90 → 95/95)
- Test Results section (update count)
- Project Status (add milestone)

**Step 3: Verify README.md was updated correctly**

```bash
git diff README.md
```

Expected: Show updates to all proposed sections

**Step 4: Revert test commit**

```bash
git reset HEAD~1
```

---

## Task 7C: Implement docs/ Folder Updates

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add docs/ folder update templates**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
### Template: Update docs/architecture.md

**When new component or architecture change detected:**

1. **Read current architecture.md**
2. **Identify section to update:**
   - "System Components" section for new modules
   - "Data Flow" section for flow changes
   - "Design Decisions" section for architectural decisions

3. **Generate component entry:**

```markdown
### [Component Name]

**Purpose:** [Brief description from docstring or code analysis]

**Location:** `src/knowledge_finder_bot/[path]/`

**Key Features:**
- [Feature 1 from code analysis]
- [Feature 2]

**Dependencies:**
- [Package 1] - [Purpose]
- [Package 2] - [Purpose]

**Integration:**
- Called by: [Component X]
- Calls: [Component Y]
```

4. **Apply edit using Edit tool**
5. **Verify by reading updated section**

---

### Template: Update docs/setup.md

**When dependency or development tool changes:**

**For new dependency:**
```markdown
## Prerequisites

- **[Package Name]** - [Purpose]
  ```bash
  # Installation
  uv add [package-name]
  ```
```

**For new environment variable:**
```markdown
## Environment Configuration

### [Variable Name]
- **Required:** [Yes/No]
- **Default:** `[default-value]`
- **Purpose:** [Description]

```bash
[VAR_NAME]=[example-value]
```
```

**For new development tool:**
```markdown
## Development Tools

### [Tool Name]
- **Purpose:** [What it does]
- **Usage:**
  ```bash
  [command]
  ```
```

---

### Template: Update docs/contributing.md

**When new coding pattern established:**

```markdown
## Code Patterns

### [Pattern Name]

**Good Example:**
```python
[good code example]
```

**Bad Example:**
```python
[bad code example]  # ❌ Avoid this
```

**Rationale:** [Why this pattern is preferred]
```

---

### Template: Update docs/deployment.md

**When deployment process changes:**

```markdown
## [Deployment Step/Section]

**Updated:** [Date]

**Changes:**
- [Change 1]
- [Change 2]

**New Process:**
```bash
[updated commands]
```

**Migration:** [Instructions for existing deployments]
```

**Application instructions:**

For each docs/ file update:
1. Read current file
2. Find appropriate section (or create new section if needed)
3. Use Edit tool to insert/update content
4. Verify by reading updated section
5. Show user the changes
```

**Step 2: Test docs/ folder updates**

Create test scenario:
```bash
# Simulate architecture change
mkdir -p src/knowledge_finder_bot/test_arch
echo '"""Test architecture component."""' > src/knowledge_finder_bot/test_arch/__init__.py
git add src/knowledge_finder_bot/test_arch
```

Run: `/update-docs`, approve

Expected: Should propose update to `docs/architecture.md` with new component section

**Step 3: Verify docs/architecture.md was updated**

```bash
git diff docs/architecture.md
```

Expected: Show new component section added

**Step 4: Clean up test changes**

```bash
git reset HEAD
rm -rf src/knowledge_finder_bot/test_arch
```

---

## Task 8: Implement Auto-Commit Feature

**Files:**
- Modify: `.claude/plugins/update-docs/commands/update-docs.md`

**Step 1: Add commit instructions to skill**

Append to `.claude/plugins/update-docs/commands/update-docs.md`:

```markdown
## Step 6: Optional Auto-Commit

**Check if user invoked with --auto-commit flag:**
- If skill was invoked as `/update-docs --auto-commit`, proceed with commit
- Otherwise, skip this step

**Commit process:**

```bash
# Stage all documentation changes
git add .claude/memory/*.md docs/*.md CLAUDE.md .env.example

# Create commit with conventional format
git commit -m "docs: update documentation for [milestone]

- Update Current Phase: [milestone] complete
- Document new dependencies: [package list]
- Add component documentation for [new modules]
- Update [other changed docs]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Commit message format:**
- **Type:** `docs:` (conventional commits)
- **Subject:** Brief summary (50 chars or less)
- **Body:** Bulleted list of specific updates
- **Footer:** Co-authored attribution

**After committing:**
- Run `git log -1 --pretty=format:"%h %s"` to show commit
- Confirm to user: "✅ Documentation committed: [hash] [subject]"
```

**Step 2: Test auto-commit**

Make test change, run: `/update-docs --auto-commit`

Expected: Should commit doc changes with proper message

**Step 3: Verify commit format**

Run: `git log -1 --pretty=format:"%s%n%b"`

Expected: Should follow conventional commits format with Co-Authored-By

**Step 4: Revert test commit**

Run: `git reset HEAD~1`

---

## Task 9: Create Hookify Rule for Proactive Detection

**Files:**
- Create: `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\hookify.detect-completion.local.md`

**Step 1: Create hookify rule file**

Create `.claude/hookify.detect-completion.local.md`:

```markdown
---
name: detect-task-completion
enabled: true
event: prompt
action: warn
pattern: (✅.*complete|✅.*implemented|all\s+\d+/\d+\s+tests\s+passing|completed\s+implementation|finished\s+(feature|task|implementation))
---

🔔 **Task completion detected!**

I noticed you completed a task. Would you like to update the documentation?

Run: `/update-docs` to analyze changes and propose documentation updates.
```

**Step 2: Verify hookify rule is loaded**

Run: `/hookify:list`

Expected: Should show "detect-task-completion" rule in list

**Step 3: Test hookify detection**

Create test change:
```bash
echo "# Test" >> src/knowledge_finder_bot/main.py
git add src/knowledge_finder_bot/main.py
```

In chat, say: "✅ Completed the test feature. All 5/5 tests passing."

Expected: Hookify should display the warning message suggesting `/update-docs`

**Step 4: Clean up test changes**

Run: `git reset HEAD src/knowledge_finder_bot/main.py && git checkout src/knowledge_finder_bot/main.py`

---

## Task 10: Update CLAUDE.md Documentation Maintenance Section

**Files:**
- Modify: `D:\latuan\Programming\AIAgent\knowledge-finder-bot\CLAUDE.md`

**Step 1: Read current Documentation Maintenance section**

Run: Read `CLAUDE.md` lines 9-48

Expected: See current manual update instructions

**Step 2: Rewrite section to promote /update-docs skill**

Replace the "Documentation Maintenance" section (lines 9-48) with:

```markdown
## 📚 Documentation Maintenance

**Use the `/update-docs` skill to keep documentation synchronized with code changes.**

### Automated Documentation Updates

This project includes an **automatic documentation update system** that:
- ✅ Detects code changes via git (new features, dependencies, env vars, etc.)
- ✅ Proposes documentation updates based on change classification
- ✅ Updates relevant files after your approval
- ✅ Optionally commits changes with conventional commit messages

**Usage:**

```bash
# After completing a feature/task
/update-docs                  # Analyze changes and propose updates
/update-docs --auto-commit    # Propose + auto-commit after approval
```

**Proactive Detection:**

When you complete a task (e.g., "✅ Feature complete, all tests passing"), the hookify rule will automatically suggest running `/update-docs`.

### Documentation Update Rules (Reference)

The `/update-docs` skill uses these mappings to determine which files to update:

| Change Type | Files to Update |
|-------------|-----------------|
| **New Feature/Module** | `README.md` (Features, Structure, Status), `docs/architecture.md`, `CLAUDE.md` (components), `.claude/memory/project-structure.md`, `.claude/memory/MEMORY.md` |
| **Dependencies** | `README.md` (Prerequisites), `docs/setup.md`, `.claude/memory/dependencies.md` |
| **Environment Variables** | `README.md` (Env Vars), `docs/setup.md`, `CLAUDE.md` (if critical), `.env.example` |
| **Code Patterns** | `.claude/memory/patterns.md`, `docs/contributing.md` (if standard) |
| **Bug Fixes/Solutions** | `.claude/memory/debugging.md`, `README.md` (if known issue) |
| **Architecture Changes** | `README.md` (Architecture, Structure), `docs/architecture.md`, `CLAUDE.md` (architecture) |
| **Development Tools** | `README.md` (Quick Start), `docs/setup.md`, `.claude/memory/MEMORY.md` |
| **Important Decisions** | `.claude/memory/decisions.md`, `docs/architecture.md` |
| **Test Results/Coverage** | `README.md` (badges, test results), `.claude/memory/MEMORY.md` |
| **Deployment Changes** | `README.md`, `docs/deployment.md` |

### Manual Updates (Fallback)

If the skill is unavailable or you prefer manual updates:

1. ✅ Identify what changed (feature, architecture, config, etc.)
2. ✅ Update relevant documentation files from table above
3. ✅ Update `.claude/memory/MEMORY.md` "Current Phase" if milestone reached
4. ✅ Verify code examples in docs still work
5. ✅ Update README.md if user-facing changes
6. ✅ Commit documentation updates WITH code changes

**Remember:** Documentation is code. Outdated docs are worse than no docs.
```

**Step 3: Apply edit using Edit tool**

Use Edit tool with exact old_string (lines 9-48) and new_string (above)

**Step 4: Verify update**

Run: Read `CLAUDE.md` lines 9-80

Expected: New section promoting `/update-docs` skill

**Step 5: Test that new CLAUDE.md section works**

Restart Claude Code session in project directory.

In new session, ask: "How should I update documentation after completing a feature?"

Expected Claude response should mention:
- `/update-docs` skill as the primary method
- Hookify proactive detection
- Manual fallback available if skill unavailable

This verifies the new CLAUDE.md instructions are being loaded correctly.

---

## Task 11: End-to-End Integration Testing

**Files:**
- Test: All components together

**Step 1: Create realistic test scenario**

Simulate completing a feature:
```bash
# 1. Create new module
mkdir -p src/knowledge_finder_bot/test_feature
cat > src/knowledge_finder_bot/test_feature/__init__.py << 'EOF'
"""Test feature for E2E testing."""

def test_function():
    """Test function."""
    return "test"
EOF

# 2. Create test file
cat > tests/test_test_feature.py << 'EOF'
"""Tests for test feature."""
from knowledge_finder_bot.test_feature import test_function

def test_test_function():
    assert test_function() == "test"
EOF

# 3. Add dependency
uv add --group dev pytest-cov

# 4. Update .env.example
echo "TEST_FEATURE_ENABLED=true" >> .env.example

# 5. Stage changes
git add src/knowledge_finder_bot/test_feature tests/test_test_feature.py pyproject.toml .env.example
```

**Step 2: Trigger completion detection**

In chat, say: "✅ Test feature implementation complete. All tests passing."

Expected: Hookify should suggest `/update-docs`

**Step 3: Run skill and verify detection**

Run: `/update-docs`

Expected output should show:
```
🔍 Detected Changes:

1. New Feature: test_feature
   📝 Documentation to update:
   ✓ .claude/memory/project-structure.md
   ✓ CLAUDE.md (Key Components)
   ✓ .claude/memory/MEMORY.md (Current Phase)

2. Dependencies: Added pytest-cov
   📝 Documentation to update:
   ✓ .claude/memory/dependencies.md

3. Environment Variables: TEST_FEATURE_ENABLED
   📝 Documentation to update:
   ✓ docs/setup.md
   ✓ CLAUDE.md
   ✓ .env.example
```

**Step 4: Approve and verify updates**

Respond: "yes"

Expected: All documentation files should be updated

**Step 5: Verify each updated file**

```bash
git diff .claude/memory/MEMORY.md
git diff .claude/memory/dependencies.md
git diff .claude/memory/project-structure.md
```

Expected: Each file should show relevant updates

**Step 6: Test auto-commit**

Run: `/update-docs --auto-commit`

Expected: Should create commit with message:
```
docs: update documentation for test feature

- Update Current Phase: test feature complete
- Document new dependencies: pytest-cov
- Add component documentation for test_feature
- Update environment variables: TEST_FEATURE_ENABLED
```

**Step 7: Clean up all test changes**

```bash
git reset HEAD~1  # Undo commit if made
git reset HEAD    # Unstage changes
rm -rf src/knowledge_finder_bot/test_feature tests/test_test_feature.py
git checkout .env.example
uv remove --group dev pytest-cov
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `/update-docs` skill appears in `/help` output
- [ ] Skill detects git changes correctly (test with new file)
- [ ] Skill classifies all 8 change types correctly
- [ ] Skill maps changes to correct doc files per CLAUDE.md table
- [ ] Skill proposes updates in readable checklist format
- [ ] Skill handles "yes", "no", "selective" approval responses
- [ ] Skill can update MEMORY.md Current Phase section
- [ ] Skill can update dependencies.md with new packages
- [ ] Skill can update project-structure.md with new modules
- [ ] `--auto-commit` flag creates proper conventional commit
- [ ] Hookify rule is loaded (shows in `/hookify:list`)
- [ ] Hookify triggers on completion keywords + git changes
- [ ] Hookify does NOT trigger when no git changes exist
- [ ] End-to-end workflow works: feature → completion → hookify → skill → edit → commit

---

## Critical Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| `C:\Users\latuan\.claude\plugins\update-docs.md` | Main skill implementation | Tasks 1-8 |
| `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\hookify.detect-completion.local.md` | Hookify rule for proactive detection | Task 9 |
| `D:\latuan\Programming\AIAgent\knowledge-finder-bot\CLAUDE.md` | Reference for update rules table (lines 27-36) | Read-only |
| `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\memory\MEMORY.md` | Primary update target (Current Phase) | Modified by skill |
| `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\memory\dependencies.md` | Dependency documentation | Modified by skill |
| `D:\latuan\Programming\AIAgent\knowledge-finder-bot\.claude\memory\project-structure.md` | Directory layout documentation | Modified by skill |

---

## Implementation Notes

**Estimated effort:**
- Tasks 1-3 (Skill foundation): 1 hour
- Tasks 4-8 (Update logic): 1.5 hours
- Task 9 (Hookify): 20 minutes
- Task 10 (Testing): 40 minutes
- **Total: ~3.5 hours**

**Success criteria:**
- Manual `/update-docs` works reliably for all 8 change types
- Hookify detects 90%+ of task completions
- Zero false positives (only triggers when appropriate)
- Documentation updates follow existing patterns
- Auto-commit creates clean, descriptive messages

**Next steps after implementation:**
1. Use the system for real features in knowledge-finder-bot
2. Monitor for false positives/negatives over 1 week
3. Refine classification logic based on real usage
4. Consider adding support for additional doc file types
5. Share this pattern with other projects
