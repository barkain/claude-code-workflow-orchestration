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

### Step 2: Verify Python Hooks

```bash
# All hooks are now Python scripts (cross-platform compatible)
# Check they exist and are readable
ls -la ~/.claude/hooks/SessionStart/
ls -la ~/.claude/hooks/UserPromptSubmit/
ls -la ~/.claude/hooks/PreToolUse/
ls -la ~/.claude/hooks/PostToolUse/
ls -la ~/.claude/hooks/SubagentStop/
ls -la ~/.claude/hooks/stop/
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

**Location:** `hooks/SessionStart/inject_all.py`

**Trigger:** Beginning of each Claude Code session (main or subagent)

**What it does:**
1. Injects orchestrator routing stub (orchestrator_stub.md, ~1.1KB)
2. Optionally injects token-efficient CLI guide (if CLAUDE_TOKEN_EFFICIENCY=1)
3. Output style is loaded natively from plugin.json (no injection)

### Problem: Stub not injected or hooks not running

**Diagnosis:**

```bash
# Verify hook is registered in plugin-hooks.json
cat ~/.claude/hooks/plugin-hooks.json | jq '.hooks.SessionStart'

# Check if Python can run the script
python3 ~/.claude/hooks/SessionStart/inject_all.py --help 2>&1 || echo "Script has issue"

# Enable debug logging to see what was injected
DEBUG_DELEGATION_HOOK=1 claude
# Then check /tmp/delegation_hook_debug.log for SessionStart activity
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Plugin not installed | Run `claude plugin install workflow-orchestrator@barkain-plugins` |
| plugin-hooks.json missing | Verify plugin installation completed |
| Python version too old | Ensure Python 3.12+ installed |

### What Gets Injected

- **Always:** Orchestrator stub (registers `/workflow-orchestrator:delegate` and `/workflow-orchestrator:bypass`)
- **Conditional:** Token-efficient CLI guide (if `CLAUDE_TOKEN_EFFICIENCY=1`, default enabled)
- **Native load:** Output style (`technical-adaptive`) loaded from plugin.json, no injection

---

## UserPromptSubmit Hook Debugging

**Location:** `hooks/UserPromptSubmit/clear-delegation-sessions.py`

**Trigger:** Before each user message is processed

**What it does:**
1. Resets per-turn nudge counter (`.claude/state/delegation_violations.json`)
2. Clears delegation active flag (`.claude/state/delegation_active`)
3. Cleans up team state files (`.claude/state/team_mode_active`, `.claude/state/team_config.json`)
4. Records turn start timestamp

### Problem: Per-turn state not being reset

**Diagnosis:**

```bash
# Check current nudge counter
cat .claude/state/delegation_violations.json

# Check if delegation_active flag exists
ls .claude/state/delegation_active

# Enable debug logging
DEBUG_DELEGATION_HOOK=1 claude
# Then prompt with any message
# Check log for "UserPromptSubmit" entries
tail /tmp/delegation_hook_debug.log
```

### Common Issues

| Issue | Solution |
|-------|----------|
| State directory doesn't exist | `mkdir -p .claude/state` |
| File permissions | `chmod 666 .claude/state/delegation_violations.json` |
| CLAUDE_PROJECT_DIR mismatch | Verify `echo $CLAUDE_PROJECT_DIR` |
| Team state not clearing | Ensure UserPromptSubmit hook is registered in plugin-hooks.json |

### Security Note

This hook is critical for security - it resets per-turn nudge counter and clears delegation/team state on each user message. Each new user interaction starts fresh.

---

## PreToolUse Hook Debugging

**Location:** `hooks/PreToolUse/require_delegation.py`

**Trigger:** Before EVERY tool invocation

**What it does (soft enforcement):**
1. Checks if tool is in the work-tool set (`Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `MultiEdit`, `NotebookEdit`)
2. If work-tool: increments per-turn violation counter and emits escalating stderr nudge
3. If subagent or delegation active: skip all checks
4. If Team tool + env var not set: block with instructions
5. All other tools: allow (no nudges for non-work tools)

### Problem: Nudges not appearing or appearing too aggressively

**Diagnosis:**

```bash
# Check current nudge counter
cat .claude/state/delegation_violations.json

# Check if delegation is active
ls .claude/state/delegation_active && echo "ACTIVE" || echo "INACTIVE"

# Enable debug mode for detailed logging
export DEBUG_DELEGATION_HOOK=1

# Test with a work tool (should increment counter)
Read some_file.py
# stderr should show nudge based on current counter

# Check debug log for counter state
tail /tmp/delegation_hook_debug.log
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Nudges always silent | Check `.claude/state/delegation_violations.json` — may be stuck at 0 |
| Nudges showing when shouldn't | Check if `delegation_active` flag file exists or if CLAUDE_PARENT_SESSION_ID is set |
| Counter not resetting | Verify UserPromptSubmit hook runs on new user message |
| Team tools blocked | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to enable team tools |

### Work Tools Reference

These 8 tools are tracked for nudges (soft enforcement, never blocked):
- `Bash` - Shell commands
- `Edit` - File editing
- `Write` - File creation
- `Read` - File reading
- `Glob` - File pattern matching
- `Grep` - File searching
- `MultiEdit` - Batch file editing
- `NotebookEdit` - Jupyter notebook editing

**All other tools** (including `AskUserQuestion`, Tasks API, `Skill`, `SlashCommand`, `Agent`, `TeamCreate`, `SendMessage`) never trigger nudges — they're always allowed.

### Agent Teams Tool Gating

Agent Teams tools (`TeamCreate`, `SendMessage`) are **not** in the unconditional allowlist. They are gated behind the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable.

**When env var is set to `1`:**

1. PreToolUse hook checks if the tool name is in the explicit set (`TeamCreate`, `SendMessage`) or matches the pattern (`"team"` or `"teammate"` in tool name, case-insensitive).
2. If matched, the tool is **allowed**.
3. On first team tool use, the hook **auto-creates** `.claude/state/team_mode_active` if it does not already exist. This state file signals downstream hooks (e.g., `validate_task_graph_compliance.py`) to skip task graph validation, since team mode handles dependencies through its own system.

**When env var is NOT set or `0`:**

1. Same matching logic applies.
2. If matched, the tool is **blocked** with an error message:
   ```
   Team tool blocked: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is not set to '1'.
   Tool: TeamCreate

   Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to enable Agent Teams.
   ```

**Debugging Agent Teams tool gating:**

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Attempt a team tool without env var (should block)
# Check log for "BLOCKED: Agent Teams tool" entry
tail /tmp/delegation_hook_debug.log

# Enable Agent Teams
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Attempt again (should allow + auto-create state file)
# Check log for "ALLOWED: Agent Teams tool" and "AUTO-CREATED" entries
tail /tmp/delegation_hook_debug.log

# Verify state file was auto-created
ls -la .claude/state/team_mode_active
```

### Problem: Task graph validation fails in team mode

**Symptom:** `validate_task_graph_compliance.py` blocks Task invocations during team mode execution.

**Diagnosis:**

```bash
# Check if team_mode_active state file exists
ls -la .claude/state/team_mode_active

# If missing, team tools haven't been used yet (auto-provisioning hasn't fired)
# Or UserPromptSubmit hook cleared it between prompts
```

**Solution:**

The `team_mode_active` state file is auto-created by the PreToolUse hook on first team tool use. If it was cleared prematurely (e.g., by a new user prompt), the team tool invocation will recreate it. No manual intervention needed.

If the file is persistently missing during an active team workflow, verify:
1. The PreToolUse hook has write access to `.claude/state/`
2. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set in the environment

---

## PostToolUse Hook Debugging

**Location:** `hooks/PostToolUse/python_posttooluse_hook.py`

**Trigger:** After Python file Write/Edit operations

**What it does (only hard-blocking hook):**
1. Runs Ruff linting for specific rule subset (F, E711, E712, UP006, UP007, UP035, UP037, T201, S)
2. Runs Pyright type checking in basic mode
3. Blocks if Ruff/Pyright fail (exit code 1 or 2)
4. Only runs on `.py` files in Write/Edit/MultiEdit tools

### Problem: Python validation failing or not running

**Diagnosis:**

```bash
# Check Python tools installed
which ruff
which pyright

# Check which Python files trigger validation
# (only .py files in Write/Edit/MultiEdit)

# Test validation manually
cd /tmp
cat > test.py << 'EOF'
def hello() -> str:
    return "world"
EOF

# Simulate Write tool
uvx ruff check --select F,E711,E712,UP006,UP007,UP035,UP037,T201,S test.py
uvx pyright test.py

# Test security check
cat > test_bad.py << 'EOF'
import pickle
data = pickle.loads(user_input)  # S301: Unsafe deserialization
EOF
uvx ruff check --select S test_bad.py
# Should fail with S301 error
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Ruff not installed | `uvx ruff check --version` or `uv tool install ruff` |
| Pyright not installed | `uvx pyright --version` or `npm install -g pyright` |
| False positives | Check `.ruff.toml` or `pyproject.toml` for rule configuration |
| Check disabled unexpectedly | Verify `CHECK_RUFF=1` and `CHECK_PYRIGHT=1` (defaults) |

### Skip Specific Checks

```bash
# Skip Ruff validation (still run Pyright)
export CHECK_RUFF=0

# Skip Pyright validation (still run Ruff)
export CHECK_PYRIGHT=0

# Skip all Python validation
export CLAUDE_SKIP_PYTHON_VALIDATION=1
```

### Validation Rules

- **Ruff subset:** F (pyflakes), E711/E712 (comparison), UP006/UP007/UP035/UP037 (modernization), T201 (print), S (security)
- **Pyright:** Type checking in basic mode
- **Enforcement:** Blocks Edit/Write on failure (hardest-blocking hook in system)

---

## SubagentStop Hook Debugging

**Location:** `hooks/SubagentStop/remind_todo_update.py` and `hooks/SubagentStop/trigger_verification.py`

**Trigger:** When a subagent (Agent-spawned agent) completes

**What these hooks do:**
- `remind_todo_update.py`: Async reminder to update task status (non-blocking)
- `trigger_verification.py`: Prompt for verification step after subagent completion

### Problem: Subagent completion not triggering reminders or verification

**Diagnosis:**

```bash
# Check if SubagentStop hooks are registered
cat ~/.claude/hooks/plugin-hooks.json | jq '.hooks.SubagentStop'

# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Watch for SubagentStop in logs
tail -f /tmp/delegation_hook_debug.log &

# Let a subagent complete and observe
# (Either through /workflow-orchestrator:delegate or Agent tool)
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Hooks not triggering | Verify `CLAUDE_PARENT_SESSION_ID` is set (set by Claude Code for subagents) |
| Reminders not appearing | Check if `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` is set (disables async hooks) |
| Async hooks blocked | On Windows, async may not work; disable with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` if problematic |

### Related

- `remind_todo_update.py` — Async, reminds to call TaskUpdate (safe to disable)
- `trigger_verification.py` — Suggests verification step before next wave

---

## Stop Hook Debugging

**Location:** `hooks/stop/python_stop_hook.py`

**Trigger:** End of main Claude Code session

**What it does:**
1. Calculates session duration (if start timestamp exists)
2. Logs quality metrics and workflow continuation signals
3. Cleans up stale task state files
4. Runs asynchronously (non-blocking)

### Problem: Session cleanup not occurring

**Diagnosis:**

```bash
# Check if Stop hook is registered
cat ~/.claude/hooks/plugin-hooks.json | jq '.hooks.Stop'

# Check turn duration state
cat .claude/state/last_turn_duration.txt
cat .claude/state/turn_durations.json

# Check for workflow continuation signal
cat .claude/state/workflow_continuation_needed.json 2>/dev/null && echo "Continuation needed" || echo "No continuation needed"

# Enable debug logging
export DEBUG_DELEGATION_HOOK=1
# Then end a session and check /tmp/delegation_hook_debug.log
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Hook not running on session exit | Verify hook registration in plugin-hooks.json |
| Async nature | Stop hook is async, so output may not display. Check state files instead. |
| Stale state not cleaning | Hook runs asynchronously; cleanup happens in background |

### Turn Duration Tracking

The Stop hook records turn duration in:
- `.claude/state/last_turn_duration.txt` — Most recent turn duration
- `.claude/state/turn_durations.json` — Last 10 durations (for sparkline in statusline)

---

## Integration Testing

### Complete Hook Lifecycle Test

This test validates the entire hook system end-to-end:

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# 1. SessionStart: Inject stub on session start
# (happens automatically at session begin)
echo "Check debug log for SessionStart activity"
tail /tmp/delegation_hook_debug.log | grep SessionStart

# 2. UserPromptSubmit: Reset per-turn state (happens on new user message)
# Submit any message to Claude Code
# Then check state was reset
cat .claude/state/delegation_violations.json  # Counter should be 0 or low

# 3. PreToolUse: Nudge on work-tool calls
# Call a work tool (e.g., Read)
Read some_file.py
# Should show nudge on stderr based on counter
cat .claude/state/delegation_violations.json  # Counter should increment

# 4. PreToolUse: Skip checks for delegation
/workflow-orchestrator:delegate "Create test.py"
# Debug log should show delegation_active flag set
cat .claude/state/delegation_violations.json  # Counter should reset to 0

# 5. PostToolUse: Validate Python file
# (happens automatically after Write on .py files)
cat > /tmp/integration_test.py << 'EOF'
def hello() -> str:
    return "world"
EOF
Write /tmp/integration_test.py
# Should complete without blocking (valid Python)

# 6. Test security validation
cat > /tmp/test_bad.py << 'EOF'
import pickle
data = pickle.loads(user_input)
EOF
Write /tmp/test_bad.py
# Should fail with S301 security error (blocks)

# 7. SubagentStop: Completion reminders (async, happens in background)
# Agent tool completion should trigger reminders

# 8. Stop: Session cleanup (happens on session end)
# Exit session and check state files are cleaned
```

### Testing Soft Enforcement

Test the nudge escalation:

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Turn 1: First work-tool call (silent or hint)
Read file1.py
# Check counter: .claude/state/delegation_violations.json

# Turn 2: Second work-tool call (nudge escalates)
# Prompt Claude with new message first
Read file2.py
# Watch stderr for escalated message

# Turn 3: Third call (warning)
Read file3.py
# Note higher-token warning message

# Use delegation to reset
/workflow-orchestrator:delegate "Create something"
# Counter resets to 0

# Next turn: Fresh start
Read file4.py
# Back to silent/hint
```

### Troubleshooting Failed Tests

If hooks aren't working:

1. **Verify plugin installation:** `ls -la ~/.claude/hooks/plugin-hooks.json`
2. **Check Python availability:** `python3 --version` (need 3.12+)
3. **Enable debug:** `export DEBUG_DELEGATION_HOOK=1` and watch `/tmp/delegation_hook_debug.log`
4. **Check state directory:** `ls -la .claude/state/` (must be writable)
5. **Verify env vars:** `echo $CLAUDE_PROJECT_DIR` (affects state file location)

### Hook Lifecycle Diagram

```
SessionStart (inject stub + optional token guide)
         |
UserPromptSubmit (reset per-turn nudge counter, clear state)
         |
User submits message
         |
PreToolUse (nudge on work-tools, validate task graph, rewrite Bash)
         |
Tool executes
         |
PostToolUse (Python validation if Write/Edit, workflow signals, depth check)
         |
SubagentStop (async reminders and verification)
         |
Stop (turn duration, cleanup)
```

---

## Related Documentation

- [Environment Variables](./environment-variables.md) - DEBUG_DELEGATION_HOOK and other settings
- [Python Coding Standards](./python-coding-standards.md) - PostToolUse validation rules
- [StatusLine System](./statusline-system.md) - Real-time status display
- [Main Documentation](../CLAUDE.md) - Complete system reference
