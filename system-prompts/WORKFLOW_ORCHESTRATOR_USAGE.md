# Workflow Orchestrator Usage Guide

## Overview

The Workflow Orchestrator system enables Claude Code to handle multi-step workflows by:
- Detecting sequential task patterns in user requests
- Decomposing them into discrete steps
- Delegating each step via `/delegate`
- Passing context between steps
- Providing consolidated results

## Files Created

### System Prompt
**Location:** `~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md`
- Contains pattern detection logic
- Defines execution strategy
- Provides examples and guidelines
- **Size:** 194 lines

### Simplified Delegation Hook
**Location:** `~/.claude/hooks/PreToolUse/require_delegation.sh`
- Blocks all tools except delegation-related ones
- Tracks delegated sessions
- **Size:** 137 lines (down from 192)
- **Removed:** Lines 17-93 (workflow detection code)

### Backup
**Location:** `~/.claude/hooks/PreToolUse/require_delegation.sh.backup-<timestamp>`
- Original hook preserved for reference

## Usage

### Option 1: Command Line Flag

Use the `--append-system-prompt` flag to load the workflow orchestrator:

```bash
claude --append-system-prompt "$(cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md)" "Create calculator and then test it"
```

### Option 2: Create an Alias

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Workflow-enabled Claude Code
alias ccw='claude --append-system-prompt "$(cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md)"'
```

Then use:

```bash
ccw "Build API and then deploy it"
ccw "Fix login bug, write tests, then commit"
ccw "Add logging to app.py and then run tests"
```

### Option 3: Project-Specific Configuration

For projects that always need workflows, add to `.claude/config.yaml`:

```yaml
system_prompts:
  - path: ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md
```

## Example Workflows

### Simple 2-Step Workflow

```bash
ccw "Create a calculator.py script and then test it"
```

**What happens:**
1. TodoWrite creates task list:
   - Create calculator.py (in_progress)
   - Test calculator.py (pending)
2. Delegates: "Create calculator.py with basic operations"
3. After completion, updates TodoWrite
4. Delegates: "Run tests for calculator.py at /path/to/calculator.py"
5. Provides final summary with results

### Complex 4-Step Workflow

```bash
ccw "Add logging to app.py, run tests, fix any issues, then commit"
```

**What happens:**
1. TodoWrite creates 4 tasks
2. Delegates each sequentially
3. Passes context between steps
4. If step fails (e.g., tests break), asks user how to proceed
5. Final summary shows all completed steps

### Build and Deploy

```bash
ccw "Build the Docker image and then deploy it to staging"
```

**What happens:**
1. Build Docker image
2. Pass image tag to deployment step
3. Deploy with specific image
4. Report both build details and deployment status

## Pattern Detection

The orchestrator detects multi-step requests by looking for:

**Sequential connectors:**
- "and then", "then", ", then"
- "after that", "next", "followed by"

**Multi-step patterns:**
- "implement X and test Y"
- "create X, write Y, run Z"
- "build X and deploy it"
- "fix X and verify Y"

**Examples:**

```bash
# ✅ Detected as workflow
ccw "Create hello.py and then run it"
ccw "Fix bug and verify it works"
ccw "Add feature, test it, then commit"

# ❌ NOT detected as workflow (single compound task)
ccw "Create calculator with tests"
ccw "Fix and test the login bug"
```

## Verification

### Check Hook is Simplified

```bash
wc -l ~/.claude/hooks/PreToolUse/require_delegation.sh
# Should show: 137 lines

# Verify no workflow detection code
grep -c "WORKFLOW DETECTION" ~/.claude/hooks/PreToolUse/require_delegation.sh
# Should show: 0 (removed)
```

### Check Backup Exists

```bash
ls -lh ~/.claude/hooks/PreToolUse/require_delegation.sh.backup-*
# Should show backup file with timestamp
```

### Test Hook Still Blocks Tools

```bash
# Without delegation, tools should be blocked
claude "What files are in my home directory?"
# Should fail with: "🚫 Tool blocked by delegation policy"

# With delegation, should work
claude "List files in my home directory" --delegate
# Should succeed
```

### Test System Prompt Loads

```bash
# Test that system prompt is readable
cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md | head -20
# Should show the system prompt header

# Test with alias
ccw --version
# Should work (verifies alias is set up correctly)
```

## How It Works

### Separation of Concerns

**Delegation Hook (require_delegation.sh):**
- **Purpose:** Block tools, enforce delegation
- **Scope:** Security/policy layer
- **Logic:** Simple allowlist, session tracking
- **Size:** 137 lines

**System Prompt (WORKFLOW_ORCHESTRATOR.md):**
- **Purpose:** Orchestrate multi-step workflows
- **Scope:** Task decomposition and execution
- **Logic:** Pattern detection, context passing, TodoWrite integration
- **Size:** 194 lines

**Key Insight:** Hook doesn't need to know about workflows. It just blocks tools. System prompt handles all workflow logic.

### Execution Flow

```
User Request: "Create app.py and then test it"
              ↓
System Prompt: Detects workflow pattern
              ↓
TodoWrite: Creates task list
              ↓
/delegate "Create app.py"
              ↓
Hook: Allows SlashCommand
              ↓
Delegation: Executes in subagent
              ↓
System Prompt: Updates TodoWrite
              ↓
/delegate "Test app.py at /path/to/app.py"
              ↓
Final Summary: Reports all results
```

## Troubleshooting

### System Prompt Not Loading

```bash
# Verify file exists
ls -lh ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md

# Test loading manually
cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md
```

### Hook Not Blocking Tools

```bash
# Enable debug mode
export DEBUG_DELEGATION_HOOK=1

# Try blocked operation
claude "Read my config file"

# Check debug log
tail -20 /tmp/delegation_hook_debug.log
```

### Workflow Not Detected

The system prompt only activates when:
1. Hook blocks a tool
2. User request has multi-step pattern
3. System prompt is loaded via `--append-system-prompt`

If workflows aren't being detected, ensure:
- You're using `ccw` alias or `--append-system-prompt` flag
- Request has sequential connectors ("and then", "then")
- Request has multiple distinct tasks

## Advanced Usage

### Combine with Other System Prompts

```bash
claude \
  --append-system-prompt "$(cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md)" \
  --append-system-prompt "$(cat ~/.claude/system-prompts/CUSTOM_RULES.md)" \
  "Create and test calculator"
```

### Environment Variables

```bash
# Disable hook temporarily (emergency bypass)
DELEGATION_HOOK_DISABLE=1 claude "Direct command"

# Enable hook debugging
DEBUG_DELEGATION_HOOK=1 ccw "Create and test app"
```

### Clean Up Old Sessions

```bash
# Hook automatically cleans up sessions older than 1 hour
# Manual cleanup:
rm -f ~/.claude/state/delegated_sessions.txt
```

## Benefits

### Before (Complex Hook)

- Hook: 192 lines with workflow detection
- Tight coupling between policy and orchestration
- Hard to maintain and debug
- Mixed responsibilities

### After (Separated)

- Hook: 137 lines, simple and focused
- System prompt: 194 lines, clear workflow logic
- Clean separation of concerns
- Easy to update either independently
- Optional: Use workflows only when needed

## Summary

**Created:**
1. `/Users/user/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md` (194 lines)
2. Simplified `/Users/user/.claude/hooks/PreToolUse/require_delegation.sh` (137 lines)
3. Backup at `/Users/user/.claude/hooks/PreToolUse/require_delegation.sh.backup-<timestamp>`

**Usage:**
```bash
# Quick usage
alias ccw='claude --append-system-prompt "$(cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md)"'
ccw "Create app and then test it"
```

**Quality Checks:**
- ✅ System prompt is clear and actionable
- ✅ Hook is simple and maintainable (137 lines vs 192)
- ✅ No dependencies between them
- ✅ Hook still blocks tools correctly
- ✅ Workflow detection moved to system prompt layer
