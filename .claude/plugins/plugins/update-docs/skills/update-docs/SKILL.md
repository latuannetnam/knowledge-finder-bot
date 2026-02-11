---
name: update-docs
description: Analyze code changes and propose documentation updates
---

# Documentation Update Assistant

This skill analyzes recent code changes and proposes documentation updates based on the project's update rules.

## Step 1: Detect Changes

### Git Status
```bash
git status --short
```

### Changed Files
```bash
git diff HEAD --name-status
```

### Recent Commit
```bash
git log -1 --pretty=format:"%h %s%n%b"
```

### Dependency Changes
```bash
git diff HEAD -- pyproject.toml | grep -E "^[+-]" | head -20
```

### Load Update Rules
```bash
cat CLAUDE.md | sed -n '27,36p'
```

### Load Current Phase
```bash
cat .claude/memory/MEMORY.md | sed -n '53,80p'
```

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

## Step 5: Execute Documentation Updates

For each approved file, use the Read and Edit tools:

### Template: Update MEMORY.md Current Phase

**Read current content:**
```bash
cat .claude/memory/MEMORY.md
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

### Template: Update dependencies.md

**When pyproject.toml changes are detected:**

1. **Extract new package from git diff:**
```bash
git diff HEAD -- pyproject.toml | grep "^+" | grep -v "^+++"
```

2. **Find where package is used:**
```bash
grep -r "import [package-name]" src/knowledge_finder_bot/ | head -5
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

### Template: Update project-structure.md

**When new module/directory is detected:**

1. **Identify new directory:**
```bash
git status --short | grep "^A" | grep "src/knowledge_finder_bot/"
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
