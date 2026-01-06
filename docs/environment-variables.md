# Environment Variables

> Reference documentation for the Claude Code Delegation System.
> Main documentation: [CLAUDE.md](../CLAUDE.md)

---

## Table of Contents

- [Overview](#overview)
- [DEBUG_DELEGATION_HOOK](#debug_delegation_hook)
- [DELEGATION_HOOK_DISABLE](#delegation_hook_disable)
- [CLAUDE_PROJECT_DIR](#claude_project_dir)
- [Configuration Examples](#configuration-examples)
- [Quick Reference](#quick-reference)

---

## Overview

The delegation system supports 3 environment variables for controlling behavior and debugging:

| Variable | Purpose | Default | Values |
|----------|---------|---------|--------|
| `DEBUG_DELEGATION_HOOK` | Enable debug logging | `0` | `0` (off), `1` (on) |
| `DELEGATION_HOOK_DISABLE` | Emergency bypass | `0` | `0` (enforcement on), `1` (enforcement off) |
| `CLAUDE_PROJECT_DIR` | Override project directory | `$PWD` | Any valid path |

---

## DEBUG_DELEGATION_HOOK

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

| Variable | Default | Enable | Disable |
|----------|---------|--------|---------|
| `DEBUG_DELEGATION_HOOK` | `0` | `export DEBUG_DELEGATION_HOOK=1` | `unset DEBUG_DELEGATION_HOOK` |
| `DELEGATION_HOOK_DISABLE` | `0` | `export DELEGATION_HOOK_DISABLE=1` | `unset DELEGATION_HOOK_DISABLE` |
| `CLAUDE_PROJECT_DIR` | `$PWD` | `export CLAUDE_PROJECT_DIR=/path` | `unset CLAUDE_PROJECT_DIR` |

### Common Commands

```bash
# Check current values
echo "DEBUG: $DEBUG_DELEGATION_HOOK"
echo "DISABLE: $DELEGATION_HOOK_DISABLE"
echo "PROJECT_DIR: $CLAUDE_PROJECT_DIR"

# Reset all to defaults
unset DEBUG_DELEGATION_HOOK
unset DELEGATION_HOOK_DISABLE
unset CLAUDE_PROJECT_DIR

# Debug mode
export DEBUG_DELEGATION_HOOK=1 && tail -f /tmp/delegation_hook_debug.log

# Emergency bypass
export DELEGATION_HOOK_DISABLE=1

# Verify state location
ls -la ${CLAUDE_PROJECT_DIR:-.}/.claude/state/
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
