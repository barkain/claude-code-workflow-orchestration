# Environment Variables

> Reference documentation for the Claude Code Delegation System.
> Main documentation: [CLAUDE.md](../CLAUDE.md)

---

## Table of Contents

- [Overview](#overview)
- [Tasks API Configuration](#tasks-api-configuration)
- [Debug & Control Variables](#debug--control-variables)
- [DEBUG_DELEGATION_HOOK](#debug_delegation_hook)
- [DELEGATION_HOOK_DISABLE](#delegation_hook_disable)
- [CLAUDE_PROJECT_DIR](#claude_project_dir)
- [Configuration Examples](#configuration-examples)
- [Quick Reference](#quick-reference)

---

## Overview

The delegation system supports several environment variables for controlling behavior and debugging:

**Tasks API Configuration (3 variables):**
- `CLAUDE_CODE_ENABLE_TASKS` - Enable/disable Tasks API integration
- `CLAUDE_CODE_TASK_LIST_ID` - Share task list across sessions
- `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` - Control async background tasks

**Debug & Control Variables (5 variables):**
- `DEBUG_DELEGATION_HOOK` - Enable debug logging
- `DELEGATION_HOOK_DISABLE` - Emergency bypass
- `CLAUDE_PROJECT_DIR` - Override project directory
- `CHECK_RUFF` - Skip Ruff validation
- `CHECK_PYRIGHT` - Skip Pyright validation

**Complete Reference Table:**

| Variable | Purpose | Default | Values |
|----------|---------|---------|--------|
| `CLAUDE_CODE_ENABLE_TASKS` | Enable Tasks API | `true` | `true`, `false` |
| `CLAUDE_CODE_TASK_LIST_ID` | Share task list | Per-session | Any list ID |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Disable async hooks | Not set | Set to `1` to disable |
| `DEBUG_DELEGATION_HOOK` | Enable debug logging | `0` | `0` (off), `1` (on) |
| `DELEGATION_HOOK_DISABLE` | Emergency bypass | `0` | `0` (enforcement on), `1` (enforcement off) |
| `CLAUDE_PROJECT_DIR` | Override project directory | `$PWD` | Any valid path |
| `CHECK_RUFF` | Skip Ruff validation | `1` | `1` (check), `0` (skip) |
| `CHECK_PYRIGHT` | Skip Pyright validation | `1` | `1` (check), `0` (skip) |

---

## Tasks API Configuration

The system uses Claude Code's native Tasks API for progress tracking. This section documents configuration variables for this integration.

### CLAUDE_CODE_ENABLE_TASKS

**Purpose:** Enable or disable Tasks API integration. When enabled (default), the system uses TaskCreate, TaskUpdate, TaskList, and TaskGet for structured task management. When disabled, reverts to legacy TodoWrite behavior.

**Values:**
- `true` (default): Tasks API enabled
- `false`: Tasks API disabled, use TodoWrite instead

**Usage:**

```bash
# Disable Tasks API and revert to TodoWrite
export CLAUDE_CODE_ENABLE_TASKS=false

# Run workflow (will use TodoWrite)
/delegate "Create calculator.py"

# Re-enable Tasks API
export CLAUDE_CODE_ENABLE_TASKS=true
```

**Task Storage:**
- Tasks are stored in `~/.claude/tasks/`
- Access via UI toggle: `Ctrl+T` in Claude Code

**When to Use:**
- Default (enabled): Recommended for all users. Provides structured metadata and better integration.
- Disabled: Only if you need legacy TodoWrite behavior or encounter Tasks API issues.

### CLAUDE_CODE_TASK_LIST_ID

**Purpose:** Share a task list across multiple Claude Code sessions. By default, each session has its own isolated task list.

**Values:**
- Default: Per-session (unique ID generated per session)
- Custom: Any task list ID string

**Usage:**

```bash
# Share task list across sessions
export CLAUDE_CODE_TASK_LIST_ID=shared_workflow

# Session 1
claude "Create part A"

# Session 2 (in new terminal)
export CLAUDE_CODE_TASK_LIST_ID=shared_workflow
claude "Create part B"

# Both sessions update the same task list
```

**When to Use:**
- **Multi-session workflows** - Coordinating work across multiple Claude Code sessions
- **Team collaboration** - Multiple team members working on the same workflow
- **Continuous workflows** - Long-running workflows split across sessions
- **Default (unset)** - Recommended for isolated, single-session workflows

### CLAUDE_CODE_DISABLE_BACKGROUND_TASKS

**Purpose:** Disable async background task features (reminders, cleanup operations). Background tasks run asynchronously via async hooks to avoid blocking the main workflow.

**Values:**
- Default: Not set (async hooks enabled)
- Disabled: Set to `1` or any truthy value

**Usage:**

```bash
# Disable background task features
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1

# Run workflow (no background reminders or cleanup)
/delegate "Long-running task"

# Re-enable background tasks
unset CLAUDE_CODE_DISABLE_BACKGROUND_TASKS
```

**Async Hooks Affected:**
- `remind_todo_after_task.py` - Async reminder after task execution
- `remind_todo_update.py` - Async reminder when updating tasks
- `python_stop_hook.py` - Async cleanup on session stop

**When to Use:**
- **Default (enabled)** - Recommended for normal workflows
- **Disabled** - Testing, performance-sensitive environments, or when background operations interfere

---

## Debug & Control Variables

### DEBUG_DELEGATION_HOOK

### Purpose

Enables detailed debug logging for delegation policy enforcement. When enabled, all hook operations are logged to `/tmp/delegation_hook_debug.log`.

### Values

- `0` (default): Debug logging disabled
- `1`: Debug logging enabled

### Usage

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Run delegation workflow
/delegate "Create calculator.py"

# Tail debug log in another terminal
tail -f /tmp/delegation_hook_debug.log
```

### Log Format

When enabled, the debug log captures:

```
[2025-01-11 14:30:22] SESSION=sess_abc123 TOOL=Read STATUS=blocked
[2025-01-11 14:30:23] SESSION=sess_abc123 TOOL=SlashCommand STATUS=allowed (triggers registration)
[2025-01-11 14:30:23] SESSION=sess_abc123 REGISTERED (delegation privileges granted)
[2025-01-11 14:30:24] SESSION=sess_abc123 TOOL=Read STATUS=allowed (session registered)
[2025-01-11 14:30:25] SESSION=sess_abc123 TOOL=Write STATUS=allowed (session registered)
[2025-01-11 14:30:26] SESSION=sess_abc123 TOOL=Bash STATUS=allowed (session registered)
```

### Log Entry Details

| Field | Description |
|-------|-------------|
| Timestamp | `[YYYY-MM-DD HH:MM:SS]` format |
| SESSION | Claude session ID |
| TOOL | Tool name being invoked |
| STATUS | `allowed`, `blocked`, or registration event |

### When to Use

- **Troubleshooting delegation policy issues** - Understand why tools are blocked/allowed
- **Debugging hook execution failures** - Identify script errors
- **Auditing tool access patterns** - Review which tools are being used
- **Verifying session registration** - Confirm delegation is working

### Performance Note

Debug logging adds overhead to every tool invocation. **Disable after troubleshooting** to avoid log file growth and performance impact.

```bash
# Disable debug logging
export DEBUG_DELEGATION_HOOK=0
# Or unset
unset DEBUG_DELEGATION_HOOK
```

### Log File Management

```bash
# Check log file size
ls -lh /tmp/delegation_hook_debug.log

# Clear log file
> /tmp/delegation_hook_debug.log

# Archive old logs
mv /tmp/delegation_hook_debug.log /tmp/delegation_hook_debug.$(date +%Y%m%d).log
```

---

## DELEGATION_HOOK_DISABLE

### Purpose

Emergency bypass to completely disable delegation enforcement. When enabled, all tools are allowed without requiring `/delegate`.

### Values

- `0` (default): Delegation enforcement enabled (tools blocked by default)
- `1`: Delegation enforcement disabled (all tools allowed)

### Usage

```bash
# Emergency bypass (disable delegation enforcement)
export DELEGATION_HOOK_DISABLE=1

# Use tools directly without /delegate
claude "Create calculator.py"

# Re-enable delegation enforcement
export DELEGATION_HOOK_DISABLE=0
# Or unset
unset DELEGATION_HOOK_DISABLE
```

### How It Works

When set to `1`:

- PreToolUse hook checks `DELEGATION_HOOK_DISABLE` first
- If set to `1`, all tools are allowed immediately
- Delegation policy is completely bypassed
- Session registry is not updated or checked
- No tools are blocked regardless of session state

### When to Use

| Scenario | Recommendation |
|----------|----------------|
| **Hook malfunction** | Use temporarily while fixing hook |
| **Testing** | Validate workflows without delegation overhead |
| **Migration** | Transitioning from non-delegated environment |
| **Emergency access** | When delegation is preventing critical work |

### Security Warnings

**This variable bypasses ALL delegation policies:**

- Tools that would normally be blocked are allowed
- No audit trail of tool usage
- No session registration or tracking
- Security controls are disabled

**Best Practices:**

1. **Use sparingly** - Only for emergencies or testing
2. **Re-enable immediately** - Don't leave disabled in production
3. **Fix the root cause** - If hooks are broken, fix them rather than bypass
4. **Document usage** - Note when and why bypass was used

### Alternative: Fix Hooks Instead

Before using bypass, try to fix the underlying issue:

```bash
# Diagnose hook issues
ls -la ~/.claude/hooks/PreToolUse/require_delegation.sh
chmod +x ~/.claude/hooks/PreToolUse/require_delegation.sh

# Test hook directly
bash -n ~/.claude/hooks/PreToolUse/require_delegation.sh
bash ~/.claude/hooks/PreToolUse/require_delegation.sh

# Check hook registration
cat ~/.claude/settings.json | jq '.hooks'
```

---

## CLAUDE_PROJECT_DIR

### Purpose

Override the project directory for state file storage. By default, state files are stored in `$PWD/.claude/state/`.

### Values

- Default: `$PWD` (current working directory)
- Custom: Any valid absolute path

### Usage

```bash
# Set project directory override
export CLAUDE_PROJECT_DIR=/Users/user/my-project

# State files written to /Users/user/my-project/.claude/state/
/delegate "Create calculator.py"

# Verify state location
ls -la /Users/user/my-project/.claude/state/
```

### How It Works

Hooks check `CLAUDE_PROJECT_DIR` when determining state file paths:

1. If `CLAUDE_PROJECT_DIR` is set, use `$CLAUDE_PROJECT_DIR/.claude/state/`
2. If not set, use `$PWD/.claude/state/`

State files affected:

- `.claude/state/delegated_sessions.txt` - Session registry
- `.claude/state/active_delegations.json` - Parallel execution tracking

### Default Behavior

Without `CLAUDE_PROJECT_DIR`, state follows the current directory:

```bash
# Without CLAUDE_PROJECT_DIR
cd /Users/user/project-a
/delegate "Task A"
# State: /Users/user/project-a/.claude/state/

cd /Users/user/project-b
/delegate "Task B"
# State: /Users/user/project-b/.claude/state/
```

### Override Behavior

With `CLAUDE_PROJECT_DIR`, state is centralized:

```bash
# With CLAUDE_PROJECT_DIR
export CLAUDE_PROJECT_DIR=/Users/user/main-project

cd /Users/user/project-a
/delegate "Task A"
# State: /Users/user/main-project/.claude/state/

cd /Users/user/project-b
/delegate "Task B"
# State: /Users/user/main-project/.claude/state/ (same location)
```

### When to Use

| Scenario | Recommendation |
|----------|----------------|
| **Multi-project workflows** | Centralize state across projects |
| **CI/CD environments** | Fixed state location regardless of build directory |
| **Debugging** | Centralized state file location for inspection |
| **Monorepo setups** | Single state directory for multiple packages |

### State File Persistence

Remember that state files are:

- Cleared on each new user prompt (by UserPromptSubmit hook)
- Cleaned up for sessions >1 hour old (by Stop hook)
- Not meant for long-term persistence

---

## Configuration Examples

### Development Environment

Optimized for debugging and development work:

```bash
# ~/.bashrc or ~/.zshrc
export DEBUG_DELEGATION_HOOK=1        # Enable debug logging
export DELEGATION_HOOK_DISABLE=0      # Enforcement enabled
export CLAUDE_PROJECT_DIR=$PWD        # Use current directory
```

Features:
- Full debug logging for troubleshooting
- Normal delegation enforcement
- State follows current directory

### Production Environment

Optimized for performance and security:

```bash
# Production environment setup
export DEBUG_DELEGATION_HOOK=0        # No debug logging (performance)
export DELEGATION_HOOK_DISABLE=0      # Enforcement enabled
export CLAUDE_PROJECT_DIR=/var/lib/claude  # Fixed state location
```

Features:
- No debug overhead
- Full security enforcement
- Centralized state management

### CI/CD Environment

Optimized for automated pipelines:

```bash
# CI/CD pipeline setup
export DEBUG_DELEGATION_HOOK=0        # No debug logging
export DELEGATION_HOOK_DISABLE=0      # Enforcement enabled
export CLAUDE_PROJECT_DIR=$CI_PROJECT_DIR/.claude  # CI workspace
```

Features:
- Clean logs (no debug noise)
- Security enforcement maintained
- State in CI workspace

### Troubleshooting Environment

Optimized for diagnosing issues:

```bash
# Troubleshooting setup
export DEBUG_DELEGATION_HOOK=1        # Full debug logging
export DELEGATION_HOOK_DISABLE=0      # Test with enforcement
export CLAUDE_PROJECT_DIR=$PWD        # Current directory

# Monitor logs
tail -f /tmp/delegation_hook_debug.log &

# Run problematic workflow
/delegate "Task that's failing"

# Check state files
cat .claude/state/delegated_sessions.txt
cat .claude/state/active_delegations.json
```

### Emergency Recovery

When delegation is blocking critical work:

```bash
# Emergency bypass (use sparingly!)
export DELEGATION_HOOK_DISABLE=1

# Complete critical task
claude "Emergency fix needed"

# Immediately re-enable
export DELEGATION_HOOK_DISABLE=0

# Investigate root cause
export DEBUG_DELEGATION_HOOK=1
/delegate "Test delegation"
tail /tmp/delegation_hook_debug.log
```

---

## Quick Reference

### Variable Summary

**Tasks API Configuration:**

| Variable | Default | Enable | Disable |
|----------|---------|--------|---------|
| `CLAUDE_CODE_ENABLE_TASKS` | `true` | `export CLAUDE_CODE_ENABLE_TASKS=true` | `export CLAUDE_CODE_ENABLE_TASKS=false` |
| `CLAUDE_CODE_TASK_LIST_ID` | Per-session | `export CLAUDE_CODE_TASK_LIST_ID=id` | `unset CLAUDE_CODE_TASK_LIST_ID` |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Not set | `export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` | `unset CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` |

**Debug & Control:**

| Variable | Default | Enable | Disable |
|----------|---------|--------|---------|
| `DEBUG_DELEGATION_HOOK` | `0` | `export DEBUG_DELEGATION_HOOK=1` | `unset DEBUG_DELEGATION_HOOK` |
| `DELEGATION_HOOK_DISABLE` | `0` | `export DELEGATION_HOOK_DISABLE=1` | `unset DELEGATION_HOOK_DISABLE` |
| `CLAUDE_PROJECT_DIR` | `$PWD` | `export CLAUDE_PROJECT_DIR=/path` | `unset CLAUDE_PROJECT_DIR` |
| `CHECK_RUFF` | `1` | `export CHECK_RUFF=1` | `export CHECK_RUFF=0` |
| `CHECK_PYRIGHT` | `1` | `export CHECK_PYRIGHT=1` | `export CHECK_PYRIGHT=0` |

### Common Commands

```bash
# Check current values
echo "TASKS_ENABLED: $CLAUDE_CODE_ENABLE_TASKS"
echo "TASK_LIST_ID: $CLAUDE_CODE_TASK_LIST_ID"
echo "BACKGROUND_DISABLED: $CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"
echo "DEBUG: $DEBUG_DELEGATION_HOOK"
echo "DISABLE: $DELEGATION_HOOK_DISABLE"
echo "PROJECT_DIR: $CLAUDE_PROJECT_DIR"

# Reset all to defaults
unset CLAUDE_CODE_ENABLE_TASKS
unset CLAUDE_CODE_TASK_LIST_ID
unset CLAUDE_CODE_DISABLE_BACKGROUND_TASKS
unset DEBUG_DELEGATION_HOOK
unset DELEGATION_HOOK_DISABLE
unset CLAUDE_PROJECT_DIR

# Tasks API specific
export CLAUDE_CODE_ENABLE_TASKS=true       # Enable Tasks API
export CLAUDE_CODE_TASK_LIST_ID=shared     # Share task list
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1  # Disable async hooks

# Debug mode
export DEBUG_DELEGATION_HOOK=1 && tail -f /tmp/delegation_hook_debug.log

# Emergency bypass
export DELEGATION_HOOK_DISABLE=1

# Verify state location
ls -la ${CLAUDE_PROJECT_DIR:-.}/.claude/state/

# View task storage
ls -la ~/.claude/tasks/
```

### Troubleshooting Matrix

| Symptom | Debug Setting | Check |
|---------|---------------|-------|
| Tools blocked unexpectedly | `DEBUG=1` | Session registration in logs |
| Hooks not running | `DEBUG=1` | Hook syntax, permissions |
| State not persisting | Check `CLAUDE_PROJECT_DIR` | State file location |
| Need immediate access | `DISABLE=1` temporarily | Fix root cause after |

---

## In-Session Delegation Bypass

The delegation system provides an interactive in-session mechanism for toggling delegation enforcement without requiring environment variables.

### The /bypass Command

**Usage:**
```bash
/bypass
```

Toggles delegation enforcement on/off from within a Claude Code session. Uses an interactive prompt to let you choose between:
- **Disable delegation (bypass hooks)** - Creates flag file, allows all tools
- **Enable delegation (enforce hooks)** - Removes flag file, normal enforcement

**Behavior:**
- Idempotent: Reports "no change needed" if already in requested state
- Persists across messages until explicitly toggled again

### Flag File Mechanism

**File Location:** `.claude/state/delegation_disabled`

| State | Flag File | Behavior |
|-------|-----------|----------|
| Enforcement enabled | Does not exist | Normal delegation enforcement |
| Enforcement disabled | Exists | All tools allowed, bypasses hooks |

### Comparison with DELEGATION_HOOK_DISABLE

| Aspect | DELEGATION_HOOK_DISABLE | /bypass |
|--------|------------------------|---------|
| Type | Environment variable | Flag file |
| Set from | Outside session (bash) | Inside session (interactive) |
| Persistence | Session lifetime | Until explicitly toggled |
| Use case | CI/CD, scripting | Debugging, troubleshooting |

---

## Related Documentation

- [Hook Debugging Guide](./hook-debugging.md) - Debug logging analysis
- [Python Coding Standards](./python-coding-standards.md) - PostToolUse validation
- [StatusLine System](./statusline-system.md) - Real-time status display
- [Main Documentation](../CLAUDE.md) - Complete system reference
