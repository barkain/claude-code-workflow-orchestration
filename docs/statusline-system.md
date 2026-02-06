# StatusLine System

> Reference documentation for the Claude Code Delegation System.
> Main documentation: [CLAUDE.md](../CLAUDE.md)

---

## Table of Contents

- [Overview](#overview)
- [Script Location](#script-location)
- [Display Components](#display-components)
- [Hook Integration](#hook-integration)
- [State Files](#state-files)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **StatusLine** is a dynamic status display system that provides real-time visibility into workflow execution state and active delegations in the Claude Code Delegation System.

### Key Features

- **Real-time updates** - Status changes as workflows progress
- **Execution mode indicator** - Shows sequential vs parallel mode
- **Active delegation count** - Tracks running subagents
- **Wave information** - Shows current wave in parallel workflows
- **Recent events** - Displays last workflow events
- **Non-blocking cost tracking** - Background cache refresh for sub-100ms response times

### Visibility

StatusLine is displayed:
- During delegation workflows
- When subagents are active
- Updated automatically by hooks

---

## Script Location

**Primary Script:** `scripts/statusline.py`

**Runtime:** Python 3.12+ (cross-platform: Windows, macOS, Linux)

### Installation

The statusline script is installed during system setup and configured via the `statusLine` field in `settings.json`:

```bash
# Verify installation
ls -la scripts/statusline.py

# Test manually (reads JSON from stdin)
echo '{}' | python3 scripts/statusline.py
```

### Script Functions

The statusline script performs:

1. **Read state files** - Loads `.claude/state/active_delegations.json`
2. **Format status** - Creates compact, color-coded display
3. **Output status** - Single-line format for terminal display
4. **Update display** - Called by hooks on state changes

---

## Display Components

### 1. Workflow Mode Indicator

Shows the current execution mode:

| Indicator | Meaning |
|-----------|---------|
| `[SEQ]` | Sequential execution mode |
| `[PAR]` | Parallel execution mode |

### 2. Active Delegations Counter

Shows the number of currently running subagents:

```
Active: 2
```

- `Active: 0` - No subagents running
- `Active: 3` - Three subagents executing concurrently

### 3. Wave Information (Parallel Mode)

Shows the current wave in parallel workflows:

```
Wave 1
Wave 2
```

Waves execute sequentially, with all subagents in a wave completing before the next wave starts.

### 4. Recent Events

Shows the last significant workflow event:

```
Last: Phase-A completed (113s)
Last: Wave 1 sync complete
Last: delegation-orchestrator started
```

### Complete Display Format

```
[MODE] Active: N Wave W | Last: Event description
```

**Examples:**

```
[SEQ] Active: 1 | Last: code-cleanup-optimizer started
[PAR] Active: 3 Wave 1 | Last: Phase-A started
[PAR] Active: 2 Wave 1 | Last: Phase-B completed (87s)
[PAR] Active: 0 Wave 2 | Last: Wave 1 sync complete
[SEQ] Active: 0 | Last: Workflow complete
```

---

## Hook Integration

The StatusLine is updated by hooks throughout the workflow lifecycle.

### Hook Update Flow

```
SessionStart Hook
    |
    v
StatusLine: [SEQ] Active: 0 | Last: Session initialized
    |
    v
PreToolUse Hook (on delegation)
    |
    v
StatusLine: [SEQ] Active: 1 | Last: delegation-orchestrator started
    |
    v
Task Tool (spawns subagents)
    |
    v
StatusLine: [PAR] Active: 3 Wave 1 | Last: Wave 1 started
    |
    v
SubagentStop Hook (subagent completes)
    |
    v
StatusLine: [PAR] Active: 2 Wave 1 | Last: Phase-A completed (113s)
    |
    v
SubagentStop Hook (wave complete)
    |
    v
StatusLine: [PAR] Active: 0 Wave 2 | Last: Wave 1 sync complete
    |
    v
Stop Hook (session ends)
    |
    v
StatusLine cleared
```

### Hook-Specific Updates

#### SessionStart Hook

```bash
# Called at session initialization
~/.claude/scripts/statusline.sh init
```

Updates StatusLine with:
- Initial mode (SEQ by default)
- Active count: 0
- Event: "Session initialized"

#### PreToolUse Hook

```bash
# Called when delegation begins
~/.claude/scripts/statusline.sh delegation_start "$AGENT_NAME"
```

Updates StatusLine with:
- Mode based on workflow plan
- Active count incremented
- Event: Agent name started

#### SubagentStop Hook

```bash
# Called when subagent completes
~/.claude/scripts/statusline.sh subagent_stop "$SESSION_ID" "$DURATION"
```

Updates StatusLine with:
- Active count decremented
- Event: Phase completed with duration
- Wave sync check (if all wave subagents complete)

#### Stop Hook

```bash
# Called at session end
~/.claude/scripts/statusline.sh clear
```

Clears StatusLine display.

---

## State Files

StatusLine reads from two state files to determine current status.

### 1. Active Delegations JSON

**Location:** `.claude/state/active_delegations.json`

**Schema:**

```json
{
  "version": "2.0",
  "workflow_id": "wf_20250111_143022",
  "execution_mode": "parallel",
  "active_delegations": [
    {
      "delegation_id": "deleg_20250111_143022_001",
      "phase_id": "phase_a",
      "session_id": "sess_abc123",
      "wave": 1,
      "status": "active",
      "started_at": "2025-01-11T14:30:22Z",
      "agent": "codebase-context-analyzer"
    },
    {
      "delegation_id": "deleg_20250111_143023_002",
      "phase_id": "phase_b",
      "session_id": "sess_def456",
      "wave": 1,
      "status": "active",
      "started_at": "2025-01-11T14:30:23Z",
      "agent": "tech-lead-architect"
    }
  ],
  "max_concurrent": 8
}
```

**Fields Used by StatusLine:**

| Field | StatusLine Component |
|-------|---------------------|
| `execution_mode` | Mode indicator (`[SEQ]`/`[PAR]`) |
| `active_delegations.length` | Active count |
| `active_delegations[].wave` | Wave number |
| `active_delegations[].agent` | Event agent name |
| `active_delegations[].status` | Completion detection |

### 2. Session Log

**Location:** `/tmp/claude_session_log.txt`

**Format:**

```
[2025-01-11 14:30:22] SESSION_START session_id=sess_abc123 type=main
[2025-01-11 14:30:25] SUBAGENT_START session_id=sess_def456 agent=codebase-context-analyzer
[2025-01-11 14:32:18] SUBAGENT_STOP session_id=sess_def456 duration=113s exit_code=0
[2025-01-11 14:35:00] SESSION_STOP session_id=sess_abc123 duration=278s
```

**Used For:**

- Recent events (last 5 entries)
- Subagent completion times
- Error messages

---

## Usage Examples

### Monitor Status in Real-Time

Open a separate terminal to watch status updates:

```bash
# Watch status updates every second
watch -n 1 ~/.claude/scripts/statusline.sh

# Or use a continuous loop
while true; do
  clear
  ~/.claude/scripts/statusline.sh
  sleep 1
done
```

### Manual Status Check

```bash
# Check current status
~/.claude/scripts/statusline.sh

# Check state file directly
cat .claude/state/active_delegations.json | jq .

# Check recent session events
tail -20 /tmp/claude_session_log.txt
```

### Debug StatusLine Output

```bash
# Enable verbose output
DEBUG=1 ~/.claude/scripts/statusline.sh

# Check what state files exist
ls -la .claude/state/

# Verify JSON validity
cat .claude/state/active_delegations.json | jq .
```

### Example Workflow Session

```bash
# Terminal 1: Monitor status
watch -n 1 ~/.claude/scripts/statusline.sh

# Terminal 2: Run workflow
/delegate "Analyze auth system AND design payment API"
```

**StatusLine progression:**

```
[SEQ] Active: 0 | Last: Session initialized
[SEQ] Active: 1 | Last: delegation-orchestrator started
[PAR] Active: 2 Wave 1 | Last: codebase-context-analyzer started
[PAR] Active: 2 Wave 1 | Last: tech-lead-architect started
[PAR] Active: 1 Wave 1 | Last: codebase-context-analyzer completed (87s)
[PAR] Active: 0 Wave 1 | Last: tech-lead-architect completed (102s)
[PAR] Active: 0 | Last: Wave 1 sync complete
[SEQ] Active: 0 | Last: Workflow complete
```

---

## Performance Optimization

The statusline cost tracking was optimized from a cold-start latency of ~28 seconds to ~0.078 seconds (360x improvement). This section documents the optimization strategy.

### Problem: Blocking Cost Fetches

The original implementation made two sequential `bunx ccusage` calls (one for daily cost, one for session cost) on every statusline refresh. Each call took ~14 seconds (package resolution + execution), resulting in a ~28-second cold start that blocked the statusline display.

### Solution: Non-Blocking Background Cache Refresh

The optimization applies three techniques:

**1. Merged API calls**

Two separate `bunx ccusage` invocations were merged into a single call using the `-i` flag, which returns per-project breakdown including daily totals. Both daily and session costs are extracted from one response.

```python
# Before: 2 sequential calls (~28s total)
# bunx ccusage daily --json --since $TODAY        # daily cost
# bunx ccusage daily --json --since $TODAY -p .   # session cost

# After: 1 call (~14s, but only in background)
# bunx ccusage daily --json --since $TODAY -i     # both values
```

**2. Background cache refresh via `subprocess.Popen`**

When the cache is expired, the statusline returns immediately with stale values (or `$...` placeholders on first run) and spawns a background process to refresh the cache. The background process uses `start_new_session=True` to fully detach from the parent.

```
Statusline call:
  1. Check cache file → valid? → return cached values (< 0.001s)
  2. Cache expired? → return stale values immediately
  3. Spawn background Python process (fire-and-forget)
  4. Background process: fetch costs → write cache file → exit
  5. Next statusline call picks up fresh cache
```

**3. Extended cache TTL**

`COST_CACHE_TTL_SECONDS` was increased from 60 to 300 seconds. Cost data changes slowly (per-session, not per-turn), making a 5-minute TTL appropriate.

**4. Lock file for concurrent refresh prevention**

A lock file (`statusline_cost_refresh.lock`) prevents multiple background refresh processes from running simultaneously. The lock is considered stale after 60 seconds.

### Performance Characteristics

| Scenario | Latency | Behavior |
|----------|---------|----------|
| Warm cache (< 300s old) | < 0.001s | Return cached values directly |
| Stale cache (> 300s old) | ~0.078s | Return stale values, spawn background refresh |
| Cold start (no cache) | ~0.078s | Return `$...` placeholders, spawn background refresh |
| Background refresh | ~14s | Runs in detached process, writes to cache file |

### Cache Files

| File | Location | Purpose |
|------|----------|---------|
| `statusline_cost_cache.json` | System temp dir | Cached daily and session costs with timestamp |
| `statusline_cost_refresh.lock` | System temp dir | Prevents concurrent background refreshes |

### Cache Schema

```json
{
  "daily_cost": "$12.34",
  "session_cost": "$3.45",
  "timestamp": 1736611822.5,
  "cwd": "/Users/user/project"
}
```

The `cwd` field is used for cache invalidation when switching between projects.

---

## Troubleshooting

### StatusLine Not Updating

**Symptom:** Status display is stale or not changing.

**Diagnosis:**

```bash
# Check script permissions
ls -la ~/.claude/scripts/statusline.sh
chmod +x ~/.claude/scripts/statusline.sh

# Check state file exists
ls -la .claude/state/active_delegations.json

# Verify hooks are calling statusline
grep statusline ~/.claude/hooks/*/*.sh

# Test script directly
~/.claude/scripts/statusline.sh
```

**Solutions:**

1. **Fix permissions:**
   ```bash
   chmod +x ~/.claude/scripts/statusline.sh
   ```

2. **Create state directory:**
   ```bash
   mkdir -p .claude/state
   ```

3. **Reinstall scripts:**
   ```bash
   cp -r src/scripts ~/.claude/
   chmod +x ~/.claude/scripts/*.sh
   ```

### StatusLine Shows Wrong Wave

**Symptom:** Wave number doesn't match expected execution phase.

**Diagnosis:**

```bash
# Check active_delegations.json schema
cat .claude/state/active_delegations.json | jq .

# Verify SubagentStop hook is updating state
tail -f /tmp/claude_session_log.txt | grep SUBAGENT_STOP

# Check wave values in state
cat .claude/state/active_delegations.json | jq '.active_delegations[].wave'
```

**Solutions:**

1. **Verify JSON structure:**
   ```bash
   # Check for JSON errors
   cat .claude/state/active_delegations.json | jq . || echo "Invalid JSON"
   ```

2. **Reset state:**
   ```bash
   rm .claude/state/active_delegations.json
   # Let next workflow recreate it
   ```

3. **Check SubagentStop hook:**
   ```bash
   bash -n ~/.claude/hooks/SubagentStop/log_subagent_stop.sh
   ```

### StatusLine Shows Wrong Active Count

**Symptom:** Active delegation count doesn't match running subagents.

**Diagnosis:**

```bash
# Count active delegations in state
cat .claude/state/active_delegations.json | jq '.active_delegations | length'

# Count running claude processes
ps aux | grep claude | grep -v grep | wc -l

# Check for orphaned entries
cat .claude/state/active_delegations.json | jq '.active_delegations[] | select(.status == "active")'
```

**Solutions:**

1. **Clear stale state:**
   ```bash
   cat .claude/state/active_delegations.json | jq '.active_delegations = []' > /tmp/clean_state.json
   mv /tmp/clean_state.json .claude/state/active_delegations.json
   ```

2. **Restart workflow:**
   ```bash
   # Clear all state
   rm -f .claude/state/active_delegations.json
   rm -f .claude/state/delegated_sessions.txt
   # Start fresh
   /delegate "Your task"
   ```

### StatusLine Script Errors

**Symptom:** Script produces errors or crashes.

**Diagnosis:**

```bash
# Check for syntax errors
bash -n ~/.claude/scripts/statusline.sh

# Run with debug output
bash -x ~/.claude/scripts/statusline.sh

# Check dependencies (jq required)
which jq || echo "jq not installed"
```

**Solutions:**

1. **Install jq:**
   ```bash
   # macOS
   brew install jq

   # Ubuntu/Debian
   sudo apt-get install jq
   ```

2. **Fix script syntax:**
   ```bash
   # Re-copy from source
   cp src/scripts/statusline.sh ~/.claude/scripts/
   chmod +x ~/.claude/scripts/statusline.sh
   ```

### No State File

**Symptom:** StatusLine shows defaults because state file doesn't exist.

**Diagnosis:**

```bash
# Check if state file exists
ls -la .claude/state/active_delegations.json

# Check if state directory exists
ls -la .claude/state/

# Check CLAUDE_PROJECT_DIR setting
echo $CLAUDE_PROJECT_DIR
```

**Solutions:**

1. **Create state directory:**
   ```bash
   mkdir -p .claude/state
   ```

2. **Initialize state file:**
   ```bash
   echo '{"version":"2.0","execution_mode":"sequential","active_delegations":[]}' > .claude/state/active_delegations.json
   ```

3. **Check project directory:**
   ```bash
   # Ensure CLAUDE_PROJECT_DIR points to correct location
   export CLAUDE_PROJECT_DIR=$PWD
   ```

---

## Related Documentation

- [Hook Debugging Guide](./hook-debugging.md) - Hook integration details
- [Environment Variables](./environment-variables.md) - CLAUDE_PROJECT_DIR setting
- [Main Documentation](../CLAUDE.md) - Complete system reference
