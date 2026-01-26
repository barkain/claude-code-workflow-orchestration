# Hook Debugging Guide

> Reference documentation for the Claude Code Delegation System.
> Main documentation: [CLAUDE.md](../CLAUDE.md)

---

## Table of Contents

- [General Hook Debugging](#general-hook-debugging)
- [SessionStart Hook Debugging](#sessionstart-hook-debugging)
- [UserPromptSubmit Hook Debugging](#userpromptsubmit-hook-debugging)
- [PreToolUse Hook Debugging](#pretooluse-hook-debugging)
- [PostToolUse Hook Debugging](#posttooluse-hook-debugging)
- [SubagentStop Hook Debugging](#subagentstop-hook-debugging)
- [Stop Hook Debugging](#stop-hook-debugging)
- [Integration Testing](#integration-testing)

---

## General Hook Debugging

The delegation system uses a comprehensive 6-hook architecture. When debugging issues, follow these systematic steps.

### Step 1: Verify Hook Installation

```bash
# Check all hooks are installed
ls -la ~/.claude/hooks/SessionStart/
ls -la ~/.claude/hooks/UserPromptSubmit/
ls -la ~/.claude/hooks/PreToolUse/
ls -la ~/.claude/hooks/PostToolUse/
ls -la ~/.claude/hooks/SubagentStop/
ls -la ~/.claude/hooks/stop/

# Check execute permissions
find ~/.claude/hooks -type f -name "*.sh" ! -perm -u+x

# Fix permissions if needed
find ~/.claude/hooks -type f -name "*.sh" -exec chmod +x {} \;
```

### Step 2: Test Hook Syntax

```bash
# Test each hook for syntax errors
bash -n ~/.claude/hooks/SessionStart/log_session_start.sh
bash -n ~/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh
bash -n ~/.claude/hooks/PreToolUse/require_delegation.sh
bash -n ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh
bash -n ~/.claude/hooks/SubagentStop/log_subagent_stop.sh
bash -n ~/.claude/hooks/stop/python_stop_hook.sh
```

### Step 3: Enable Debug Logging

```bash
# Enable global debug logging
export DEBUG_DELEGATION_HOOK=1

# Each hook will log to /tmp/delegation_hook_debug.log
tail -f /tmp/delegation_hook_debug.log
```

### Step 4: Check Hook Registration

```bash
# Verify hooks are registered in settings.json
cat ~/.claude/settings.json | jq '.hooks'

# Expected output should include all 6 hook types
```

---

## SessionStart Hook Debugging

**Location:** `src/hooks/SessionStart/log_session_start.sh`

**Trigger:** Beginning of each Claude Code session (main or subagent)

### Problem: Session not logged at startup

**Diagnosis:**

```bash
# Check session log file exists
ls -la /tmp/claude_session_log.txt

# Check recent session starts
tail -20 /tmp/claude_session_log.txt | grep SESSION_START

# Manually trigger hook
export CLAUDE_SESSION_ID=test_session
bash ~/.claude/hooks/SessionStart/log_session_start.sh

# Verify test entry in log
grep test_session /tmp/claude_session_log.txt
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Log file permissions | `chmod 666 /tmp/claude_session_log.txt` |
| CLAUDE_SESSION_ID not set | Hook needs session ID from Claude Code |
| Hook not executable | `chmod +x ~/.claude/hooks/SessionStart/log_session_start.sh` |

### Expected Log Format

```
[2025-01-11 14:30:22] SESSION_START session_id=sess_abc123 type=main
```

---

## UserPromptSubmit Hook Debugging

**Location:** `src/hooks/UserPromptSubmit/clear-delegation-sessions.sh`

**Trigger:** Before each user message is processed

### Problem: Delegation state not cleared between prompts

**Diagnosis:**

```bash
# Check state file before and after prompt
cat .claude/state/delegated_sessions.txt

# Manually trigger hook
bash ~/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh

# Verify file cleared
cat .claude/state/delegated_sessions.txt  # Should be empty
```

### Common Issues

| Issue | Solution |
|-------|----------|
| State directory doesn't exist | `mkdir -p .claude/state` |
| File permissions | `chmod 644 .claude/state/delegated_sessions.txt` |
| CLAUDE_PROJECT_DIR mismatch | Verify `echo $CLAUDE_PROJECT_DIR` |

### Security Note

This hook is critical for security - it prevents privilege persistence across user prompts. Each new user message starts with a clean delegation state.

---

## PreToolUse Hook Debugging

**Location:** `src/hooks/PreToolUse/require_delegation.sh`

**Trigger:** Before EVERY tool invocation

### Problem: Tools not blocked or session not registered

**Diagnosis:**

```bash
# Enable debug mode
export DEBUG_DELEGATION_HOOK=1

# Check allowlist configuration
grep -A 10 "ALLOWED_TOOLS" ~/.claude/hooks/PreToolUse/require_delegation.sh

# Manually test hook (requires tool name argument)
export CLAUDE_SESSION_ID=test_session
export CLAUDE_TOOL_NAME=Read
bash ~/.claude/hooks/PreToolUse/require_delegation.sh

# Check debug log
tail /tmp/delegation_hook_debug.log
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Allowlist too broad | Verify ALLOWED_TOOLS array contains only intended tools |
| Session not registered | Check `.claude/state/delegated_sessions.txt` has session ID |
| File path issues | Verify script uses correct state file path |

### Manual Session Registration Test

```bash
# Create test session
mkdir -p .claude/state
echo "test_session_123" > .claude/state/delegated_sessions.txt

# Test tool access with registered session
export CLAUDE_SESSION_ID=test_session_123
export CLAUDE_TOOL_NAME=Read
bash ~/.claude/hooks/PreToolUse/require_delegation.sh
# Should exit 0 (allowed)

# Test tool access with unregistered session
export CLAUDE_SESSION_ID=unregistered_session
bash ~/.claude/hooks/PreToolUse/require_delegation.sh
# Should exit 1 (blocked)
```

### Allowlist Reference

The following tools are always allowed without delegation:

- `AskUserQuestion` - Read-only questions
- `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet` - Task tracking via Tasks API
- `SlashCommand` - Triggers session registration
- `Task`/`SubagentTask`/`AgentTask` - Triggers session registration

All other tools are BLOCKED unless session is registered.

---

## PostToolUse Hook Debugging

**Location:** `src/hooks/PostToolUse/python_posttooluse_hook.sh`

**Trigger:** After Python file Write/Edit operations

### Problem: Python validation not running or failing incorrectly

**Diagnosis:**

```bash
# Check Python tools installed
which ruff
which pyright

# Test hook manually with Python file
export CLAUDE_TOOL_NAME=Write
export CLAUDE_TOOL_ARGUMENTS='{"file_path":"/tmp/test.py","content":"print(\"hello\")"}'
bash ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh

# Check exit code
echo $?  # 0 = success, 1 = validation failed

# Test critical security check
cat > /tmp/test_bad.py << 'EOF'
import pickle
data = pickle.loads(user_input)  # S301: Unsafe deserialization
EOF

export CLAUDE_TOOL_ARGUMENTS='{"file_path":"/tmp/test_bad.py"}'
bash ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh
# Should fail with S301 error
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Ruff not installed | `uv tool install ruff` or `pip install ruff` |
| Pyright not installed | `npm install -g pyright` |
| Tool name not Write/Edit | Hook only runs for Write/Edit operations |
| JSON parsing error | Verify CLAUDE_TOOL_ARGUMENTS is valid JSON |

### Skip Specific Checks

```bash
# Skip Ruff validation
export CHECK_RUFF=0
bash ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh

# Skip Pyright validation
export CHECK_PYRIGHT=0
bash ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh
```

### Validation Stages

1. **Critical Security Check** - Fast pattern matching for immediate vulnerabilities
2. **Ruff Validation** - Comprehensive linting for syntax, security, and quality
3. **Pyright Type Checking** - Type annotation validation (basic mode)

---

## SubagentStop Hook Debugging

**Location:** `src/hooks/SubagentStop/log_subagent_stop.sh`

**Trigger:** When a subagent (Task-spawned agent) completes

### Problem: Subagent completion not logged or parallel state not updated

**Diagnosis:**

```bash
# Check session log for subagent stops
tail -50 /tmp/claude_session_log.txt | grep SUBAGENT_STOP

# Check parallel execution state
cat .claude/state/active_delegations.json | jq .

# Manually trigger hook
export CLAUDE_SESSION_ID=test_subagent
export CLAUDE_PARENT_SESSION_ID=test_parent
bash ~/.claude/hooks/SubagentStop/log_subagent_stop.sh

# Verify log entry
grep test_subagent /tmp/claude_session_log.txt
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Parent session ID missing | Hook needs CLAUDE_PARENT_SESSION_ID |
| active_delegations.json corrupted | Check JSON syntax with `jq` |
| Wave synchronization failure | Verify all Wave N subagents have SUBAGENT_STOP entries |

### Test Wave Synchronization

```bash
# Create test parallel workflow state
cat > .claude/state/active_delegations.json << 'EOF'
{
  "version": "2.0",
  "workflow_id": "test_workflow",
  "execution_mode": "parallel",
  "active_delegations": [
    {"delegation_id": "d1", "session_id": "s1", "wave": 1, "status": "active"},
    {"delegation_id": "d2", "session_id": "s2", "wave": 1, "status": "active"}
  ]
}
EOF

# Simulate first subagent stop
export CLAUDE_SESSION_ID=s1
bash ~/.claude/hooks/SubagentStop/log_subagent_stop.sh

# Check d1 marked complete
cat .claude/state/active_delegations.json | jq '.active_delegations[] | select(.delegation_id=="d1")'

# Simulate second subagent stop (should trigger wave sync)
export CLAUDE_SESSION_ID=s2
bash ~/.claude/hooks/SubagentStop/log_subagent_stop.sh

# Check both complete
cat .claude/state/active_delegations.json | jq '.active_delegations'
```

### Expected Log Format

```
[2025-01-11 14:32:15] SUBAGENT_STOP session_id=sess_def456 parent=sess_abc123 duration=113s exit_code=0
```

---

## Stop Hook Debugging

**Location:** `src/hooks/stop/python_stop_hook.sh`

**Trigger:** End of main Claude Code session

### Problem: Session cleanup not occurring

**Diagnosis:**

```bash
# Check session log for STOP entries
tail -50 /tmp/claude_session_log.txt | grep SESSION_STOP

# Check stale session cleanup
ls -la .claude/state/delegated_sessions.txt
stat .claude/state/delegated_sessions.txt  # Check file age

# Manually trigger hook
export CLAUDE_SESSION_ID=test_session
bash ~/.claude/hooks/stop/python_stop_hook.sh

# Verify log entry
grep "SESSION_STOP.*test_session" /tmp/claude_session_log.txt
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Hook not running on exit | Verify hook registration in settings.json |
| Stale sessions not cleaned | Check cleanup logic (removes sessions >1 hour old) |
| State validation errors | Check parallel workflow state schema |

### Test Stale Session Cleanup

```bash
# Create old session entry
mkdir -p .claude/state
echo "old_session_123" > .claude/state/delegated_sessions.txt

# Age the file (macOS/BSD syntax)
touch -t 202501010000 .claude/state/delegated_sessions.txt

# Run stop hook (should remove old session)
bash ~/.claude/hooks/stop/python_stop_hook.sh

# Verify file cleaned
cat .claude/state/delegated_sessions.txt  # Should be empty or removed
```

### Expected Log Format

```
[2025-01-11 14:35:00] SESSION_STOP session_id=sess_abc123 duration=278s
```

---

## Integration Testing

### Complete Hook Lifecycle Test

This test validates the entire hook system end-to-end:

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# 1. SessionStart: Initialize
export CLAUDE_SESSION_ID=integration_test_001
bash ~/.claude/hooks/SessionStart/log_session_start.sh
grep SESSION_START /tmp/claude_session_log.txt | tail -1

# 2. UserPromptSubmit: Clear state
bash ~/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh
cat .claude/state/delegated_sessions.txt  # Should be empty

# 3. PreToolUse: Block Read (not registered)
export CLAUDE_TOOL_NAME=Read
bash ~/.claude/hooks/PreToolUse/require_delegation.sh && echo "FAIL: Should block" || echo "PASS: Blocked"

# 4. PreToolUse: Allow SlashCommand (triggers registration)
export CLAUDE_TOOL_NAME=SlashCommand
bash ~/.claude/hooks/PreToolUse/require_delegation.sh && echo "PASS: Allowed" || echo "FAIL: Should allow"
cat .claude/state/delegated_sessions.txt  # Should contain integration_test_001

# 5. PreToolUse: Allow Read (now registered)
export CLAUDE_TOOL_NAME=Read
bash ~/.claude/hooks/PreToolUse/require_delegation.sh && echo "PASS: Allowed" || echo "FAIL: Should allow"

# 6. PostToolUse: Validate Python file
cat > /tmp/integration_test.py << 'EOF'
def hello() -> str:
    return "world"
EOF
export CLAUDE_TOOL_NAME=Write
export CLAUDE_TOOL_ARGUMENTS='{"file_path":"/tmp/integration_test.py"}'
bash ~/.claude/hooks/PostToolUse/python_posttooluse_hook.sh && echo "PASS: Validation" || echo "FAIL: Validation"

# 7. SubagentStop: Log completion
export CLAUDE_PARENT_SESSION_ID=integration_test_001
export CLAUDE_SESSION_ID=integration_test_subagent
bash ~/.claude/hooks/SubagentStop/log_subagent_stop.sh
grep SUBAGENT_STOP /tmp/claude_session_log.txt | tail -1

# 8. Stop: Cleanup
export CLAUDE_SESSION_ID=integration_test_001
bash ~/.claude/hooks/stop/python_stop_hook.sh
grep SESSION_STOP /tmp/claude_session_log.txt | tail -1

# Verify complete lifecycle in debug log
tail -100 /tmp/delegation_hook_debug.log | grep integration_test
```

### Expected Output

```
SESSION_START session_id=integration_test_001
PASS: Blocked
PASS: Allowed
integration_test_001 (in delegated_sessions.txt)
PASS: Allowed
PASS: Validation
SUBAGENT_STOP session_id=integration_test_subagent parent=integration_test_001
SESSION_STOP session_id=integration_test_001
```

### Troubleshooting Failed Integration Tests

If any step fails, check:

1. **Hook script syntax:** `bash -n <script>`
2. **Permissions:** `ls -la`, `chmod +x`
3. **Environment variables:** `env | grep CLAUDE`
4. **Debug log:** `tail /tmp/delegation_hook_debug.log`

### Hook Lifecycle Diagram

```
SessionStart (initialize)
         |
UserPromptSubmit (clear delegation state)
         |
Main Claude receives message
         |
PreToolUse (check/block tools, register session)
         |
Tool executes
         |
PostToolUse (validate Python code if Write/Edit)
         |
SubagentStop (if subagent completes)
         |
Stop (cleanup on session exit)
```

---

## Related Documentation

- [Environment Variables](./environment-variables.md) - DEBUG_DELEGATION_HOOK and other settings
- [Python Coding Standards](./python-coding-standards.md) - PostToolUse validation rules
- [StatusLine System](./statusline-system.md) - Real-time status display
- [Main Documentation](../CLAUDE.md) - Complete system reference
