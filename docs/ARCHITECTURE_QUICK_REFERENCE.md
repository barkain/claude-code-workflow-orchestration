# Architecture Quick Reference Guide

> Fast-access reference for the Claude Code Workflow Orchestration System.
> For comprehensive documentation, see [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md).

---

## Table of Contents

1. [Decision Trees](#decision-trees)
2. [Agent Reference Tables](#agent-reference-tables)
3. [State File Reference](#state-file-reference)
4. [Hook Reference](#hook-reference)
5. [Debugging Checklists](#debugging-checklists)
6. [Common Patterns](#common-patterns)
7. [Team Mode Quick Reference](#team-mode-quick-reference)

---

## Decision Trees

### Should I Use /workflow-orchestrator:delegate?

```
Is the task blocked by PreToolUse hook?
├── YES → Use /workflow-orchestrator:delegate immediately
│         Do NOT try alternative tools
│
└── NO → 3-Step Routing Check:
         │
         Step 1: Does task require Write/Edit?
         ├── NO → Use /workflow-orchestrator:delegate (spawns Explore agents or codebase-context-analyzer)
         │
         └── YES → Step 2: Is this a breadth task (many files)?
                   ├── YES → Use /workflow-orchestrator:delegate (parallel Explore agents)
                   │
                   └── NO → Step 3: Is task simple?
                            ├── YES → DIRECT EXECUTION (bypass plan mode)
                            │
                            └── NO → Use /workflow-orchestrator:delegate for complex tasks
```

### Which Agent Will Handle My Task?

```
Count keyword matches in task description:

Does task contain >= 2 of: analyze, understand, explore, architecture, patterns, structure, dependencies?
├── YES → codebase-context-analyzer (read-only analysis)

Does task contain >= 2 of: refactor, cleanup, optimize, improve, technical debt, maintainability?
├── YES → code-cleanup-optimizer (implementation)

Does task contain >= 2 of: verify, validate, test, check, review, quality, edge cases?
├── YES → task-completion-verifier (verification)

Does task contain >= 2 of: design, approach, research, evaluate, best practices, architect?
├── YES → tech-lead-architect (design)

Does task contain >= 2 of: review, code review, critique, feedback, assess quality, evaluate code?
├── YES → code-reviewer (read-only)

Does task contain >= 2 of: setup, deploy, docker, CI/CD, infrastructure, pipeline, configuration?
├── YES → devops-experience-architect (implementation)

Does task contain >= 2 of: document, write docs, README, explain, create guide, documentation?
├── YES → documentation-expert (implementation)

Does task contain >= 2 of: dependencies, packages, requirements, install, upgrade, manage packages?
├── YES → dependency-manager (implementation)

No agent >= 2 matches?
└── general-purpose delegation
```

### Sequential vs Parallel Execution?

```
Are phases dependent?
├── Phase B reads files from Phase A? → SEQUENTIAL
├── Both phases modify same file? → SEQUENTIAL
├── Both phases affect same state? → SEQUENTIAL
├── API rate limits apply? → SEQUENTIAL
│
└── NO dependencies detected
    └── Does task contain uppercase "AND"?
        ├── YES → Check for conflicts
        │         ├── Conflicts found → SEQUENTIAL
        │         └── No conflicts → PARALLEL
        │
        └── NO → Default to SEQUENTIAL (conservative)
```

### Subagent vs Team Mode?

```
Is TeamCreate tool available?
├── NO → SUBAGENT MODE (always)
│        (Tool not available when CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set)
│
└── YES → TEAM MODE
          TeamCreate + Agent(team_name=...) for all phases
          Teammates communicate via SendMessage
          
          (No scoring — tool availability is the only signal)
```

### Is Task Atomic?

```
Is depth < 3?
├── YES → NOT ATOMIC (must decompose)

At depth >= 3, check ALL criteria:

1. Time < 30 minutes?
   └── NO → NOT ATOMIC

2. Files <= 3?
   └── NO → NOT ATOMIC

3. Single deliverable?
   └── NO → NOT ATOMIC

4. No planning required?
   └── NO → NOT ATOMIC

5. Single responsibility (no "and" connecting verbs)?
   └── NO → NOT ATOMIC

6. Expressible in 2-3 sentences?
   └── NO → NOT ATOMIC

ALL criteria met?
├── YES → ATOMIC (leaf node)
└── NO → NOT ATOMIC (decompose further)
```

---

## Agent Reference Tables

### Agent Capabilities Matrix

| Agent | Read | Write | Edit | Bash | Agent | Glob | Grep |
|-------|:----:|:-----:|:----:|:----:|:----:|:----:|:----:|
| codebase-context-analyzer | Y | - | - | Y | - | Y | Y |
| tech-lead-architect | Y | Y | Y | Y | - | Y | Y |
| task-completion-verifier | Y | - | - | Y | - | Y | Y |
| code-cleanup-optimizer | Y | Y | Y | Y | - | Y | Y |
| code-reviewer | Y | - | - | Y | - | Y | Y |
| devops-experience-architect | Y | Y | Y | Y | - | Y | Y |
| documentation-expert | Y | Y | Y | Y | - | Y | Y |
| dependency-manager | Y | Y | Y | Y | - | - | - |

**Legend:** Y = Has access, - = No access

**Team Mode:** All agents include a conditional COMMUNICATION MODE. As teammates, they send completion messages via SendMessage and proactively notify peers of cross-cutting issues. As subagents spawned via Agent, they return only `DONE|{path}`.

### Agent Selection Keywords

| Agent | Primary Keywords | Secondary Keywords |
|-------|-----------------|-------------------|
| codebase-context-analyzer | analyze, architecture | understand, explore, patterns, structure, dependencies |
| code-cleanup-optimizer | refactor, optimize | cleanup, improve, technical debt, maintainability |
| task-completion-verifier | verify, validate | test, check, review, quality, edge cases |
| tech-lead-architect | design, architect | approach, research, evaluate, best practices, scalability, security |
| code-reviewer | review, code review | critique, feedback, assess quality, evaluate code |
| devops-experience-architect | deploy, docker | setup, CI/CD, infrastructure, pipeline, configuration |
| documentation-expert | document, documentation | write docs, README, explain, create guide |
| dependency-manager | dependencies, packages | requirements, install, upgrade, manage packages |

### Agent Use Cases

| Use Case | Recommended Agent | Rationale |
|----------|------------------|-----------|
| "How does auth work?" | codebase-context-analyzer | Read-only exploration |
| "Refactor for maintainability" | code-cleanup-optimizer | Implementation focus |
| "Test the calculator" | task-completion-verifier | Verification focus |
| "Design API architecture" | tech-lead-architect | Design/planning focus |
| "Review PR changes" | code-reviewer | Objective assessment |
| "Set up Docker" | devops-experience-architect | Infrastructure focus |
| "Update README" | documentation-expert | Documentation focus |
| "Add pytest dependency" | dependency-manager | Package management |

---

## State File Reference

### delegation_violations.json

**Location:** `.claude/state/delegation_violations.json`

**Format:** Per-turn nudge counter
```json
{
  "violations": 2,
  "delegations": 0,
  "turn_id": "turn_2025_04_07_143022"
}
```

**Operations:**
```bash
# Check current nudge counter
cat .claude/state/delegation_violations.json

# Reset counter to 0
echo '{"violations": 0, "delegations": 0}' > .claude/state/delegation_violations.json
```

**Lifecycle:**
- Reset to 0 on each new user prompt (UserPromptSubmit hook)
- Increments on each work-tool call (PreToolUse hook)
- Resets to 0 when `/workflow-orchestrator:delegate` runs (remind_skill_continuation.py hook)

### delegation_active

**Location:** `.claude/state/delegation_active`

**Format:** Empty marker file (presence indicates active delegation)

**Operations:**
```bash
# Check if delegation is active
test -f .claude/state/delegation_active && echo "ACTIVE" || echo "INACTIVE"

# Manually activate (emergency)
touch .claude/state/delegation_active

# Manually deactivate
rm -f .claude/state/delegation_active
```

**Lifecycle:**
- Created when delegation begins (nudges suppressed)
- Deleted when delegation ends
- Suppresses work-tool nudges while active

### active_delegations.json

**Location:** `.claude/state/active_delegations.json`

**Schema:**
```json
{
  "version": "2.0",
  "workflow_id": "wf_YYYYMMDD_HHMMSS",
  "execution_mode": "sequential|parallel",
  "active_delegations": [
    {
      "delegation_id": "deleg_YYYYMMDD_HHMMSS_NNN",
      "phase_id": "phase_N_M",
      "session_id": "sess_XXX",
      "wave": 0,
      "status": "active|completed|failed",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "agent": "agent-name"
    }
  ],
  "max_concurrent": 8
}
```

**Concurrency Enforcement:** The `max_concurrent` field (default: 8, configurable via `CLAUDE_MAX_CONCURRENT` env var) limits parallel agent spawns. Waves with more parallel phases than this limit are executed in batches to prevent context exhaustion.

**Simplified State:** The `delegation_active` flag (boolean) replaces complex session registration for subagent detection.

**Operations:**
```bash
# View current state
cat .claude/state/active_delegations.json | jq .

# Count active delegations
cat .claude/state/active_delegations.json | jq '.active_delegations | length'

# Find active phases
cat .claude/state/active_delegations.json | jq '.active_delegations[] | select(.status == "active")'

# Reset state
echo '{"version":"2.0","execution_mode":"sequential","active_delegations":[]}' > .claude/state/active_delegations.json
```

### active_task_graph.json

**Location:** `.claude/state/active_task_graph.json`

**Schema:**
```json
{
  "task_id": "root",
  "tier": 1|2|3,
  "complexity_score": N,
  "waves": [
    {
      "wave_id": 0,
      "parallel_execution": true|false,
      "phases": [
        {
          "phase_id": "phase_N_M",
          "type": "implementation|verification",
          "agent": "agent-name",
          "status": "pending|in_progress|completed|failed"
        }
      ]
    }
  ],
  "current_wave": 0
}
```

### team_mode_active (Team Mode)

**Location:** `.claude/state/team_mode_active`

**Format:** Empty marker file (presence = team mode active)

**Lifecycle:**
1. Auto-created by PreToolUse hook when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and a team tool is invoked
2. Can also be created by plan mode or lead agent during Step 1
3. Cleared by UserPromptSubmit hook or during team cleanup (Step 5)

**Operations:**
```bash
# Check if team mode is active
test -f .claude/state/team_mode_active && echo "ACTIVE" || echo "INACTIVE"

# Manually activate (emergency)
touch .claude/state/team_mode_active

# Manually deactivate
rm -f .claude/state/team_mode_active
```

### team_config.json (Team Mode)

**Location:** `.claude/state/team_config.json`

**Schema:**
```json
{
  "team_name": "workflow-20250206_143022",
  "lead_mode": "delegate",
  "plan_approval": true,
  "max_teammates": 4,
  "teammate_roles": [
    {
      "role_name": "implementer",
      "agent_config": "code-cleanup-optimizer",
      "phase_ids": ["phase_0_0", "phase_0_1"]
    },
    {
      "role_name": "reviewer",
      "agent_config": "task-completion-verifier",
      "phase_ids": ["phase_2_0"]
    }
  ]
}
```

**Operations:**
```bash
# View team configuration
cat .claude/state/team_config.json | jq .

# Check team name
cat .claude/state/team_config.json | jq -r '.team_name'

# List teammate roles
cat .claude/state/team_config.json | jq '.teammate_roles[].role_name'

# Reset team state
rm -f .claude/state/team_mode_active .claude/state/team_config.json
```

---

## Hook Reference

### Hook Execution Order

```
1. SessionStart       (session begins)
2. UserPromptSubmit   (before user message)
3. PreToolUse         (before each tool)
4. [Tool Executes]
5. PostToolUse        (after each tool)
6. SubagentStop       (subagent completes)
7. Stop               (session ends)
```

### Hook Quick Reference

| Hook | Trigger | Key Actions | Async | Timeout |
|------|---------|-------------|-------|---------|
| SessionStart | startup, resume, clear, compact | Inject stub + optional token guide | - | 20s |
| UserPromptSubmit | Before user message | Reset nudge counter, clear state | - | 2s |
| PreToolUse (*) | Before every tool | Soft nudges on work tools, task graph validation, Bash rewrite | - | 5s each |
| PostToolUse (Write/Edit) | After Python file changes | Ruff + Pyright validation (hard-blocking) | - | default |
| PostToolUse (Task/Skill/SlashCommand) | After Agent, Task, or command | Workflow signals, reset nudge counter on delegation | - | 2s |
| PostToolUse (Agent/Task) | After Agent or Task tool | Depth validation, task metadata | - | 5s each |
| SubagentStop | Subagent completes | Task reminder (async), verification trigger | Yes | 2-5s |
| Stop | Session ends | Turn duration, workflow continuation | Yes | default |

**Async Hooks (controlled by CLAUDE_CODE_DISABLE_BACKGROUND_TASKS):**
- `remind_todo_after_task.py` - Reminder after task execution (async)
- `remind_todo_update.py` - Reminder on task updates (async)
- `python_stop_hook.py` - Cleanup on session stop (async)

### Allowlist & Nudge Reference

**Always Allowed (never tracked for nudges):**
- `AskUserQuestion` - Read-only questions
- `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet` - Native task tracking with structured metadata
- `SlashCommand` - Commands (resets nudge counter if delegation runs)
- `Skill` - Skill invocation
- `ToolSearch` - Discover and load deferred tools
- `Agent`/`SubagentTask`/`AgentTask` - Delegation mechanism

**Work Tools (tracked for soft nudges, NEVER blocked):**
- `Bash` - Shell commands
- `Edit` - File editing
- `Write` - File creation
- `Read` - File reading
- `Glob` - File pattern matching
- `Grep` - File searching
- `MultiEdit` - Batch file editing
- `NotebookEdit` - Jupyter editing

**Conditionally Allowed (Agent Teams, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):**
- `TeamCreate` - Create a named agent team
- `SendMessage` - Inter-teammate communication
- Any tool name containing "team" or "teammate" (case-insensitive safety net)

**Write Tool Safe Paths (always allowed):**
- `/tmp/` - Temporary files
- `/private/tmp/` - macOS private temp
- `/var/folders/` - macOS user temp
- `$CLAUDE_SCRATCHPAD_DIR` - Agent output scratchpad

**Subagent Detection:** When `CLAUDE_PARENT_SESSION_ID` is set, hooks are skipped (subagent context).

**Note:** Tasks API replaced TodoWrite. Task metadata includes: wave, phase_id, agent, and parallel flag for structured execution tracking.

**PROHIBITED (Context Exhaustion):**
- `TaskOutput` - Causes context window exhaustion (~20K per agent)
- `TaskList` polling loops - Use completion notifications instead
- Agents returning full results - Return `DONE|{path}` only

---

## Debugging Checklists

### Tools Not Working

- [ ] Is session registered? Check `.claude/state/delegated_sessions.txt`
- [ ] Was `/workflow-orchestrator:delegate` used? Use it immediately when blocked
- [ ] Are hooks installed? Check `ls -la ~/.claude/hooks/*/`
- [ ] Are hooks executable? Run `chmod +x ~/.claude/hooks/*/*.sh`
- [ ] Check hook syntax: `bash -n <hook_script>`
- [ ] Enable debug logging: `export DEBUG_DELEGATION_HOOK=1`
- [ ] Tail debug log: `tail -f /tmp/delegation_hook_debug.log`

### Delegation Failing

- [ ] Is plan mode available? Check that EnterPlanMode/ExitPlanMode tools are accessible
- [ ] Are agent files present? Check `ls ~/.claude/agents/`
- [ ] Is settings.json configured? Check `cat ~/.claude/settings.json | jq '.hooks'`
- [ ] Reinstall if needed: `cp -r agents hooks skills ~/.claude/`
- [ ] Check routing: Simple tasks use DIRECT EXECUTION (bypass plan mode)

### Multi-Step Not Detected

- [ ] Is the SessionStart hook installed? Check `ls ~/.claude/hooks/SessionStart/inject_all.py` — it injects `orchestrator_stub.md` which routes multi-step work through `/workflow-orchestrator:delegate`.
- [ ] Does task have multi-step indicators?
  - Sequential connectors: "and then", "with", "including"
  - Multiple verbs: "create", "test", "verify"
  - Phase markers: "first... then..."
- [ ] Try explicit phrasing: "Create X and then test X"

### Parallel Not Working

- [ ] Does task contain uppercase "AND"?
- [ ] Are phases truly independent (no data dependencies)?
- [ ] Are phases modifying different files?
- [ ] Check `active_delegations.json` for execution_mode
- [ ] Orchestrator may default to sequential (conservative)

### Team Mode Not Activating

- [ ] Is `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set? Check `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
- [ ] Can you invoke TeamCreate? If blocked, env var not set correctly
- [ ] Does `team_mode_active` exist? Check `ls -la .claude/state/team_mode_active`
- [ ] Does `team_config.json` exist? Check `cat .claude/state/team_config.json | jq .`
- [ ] Enable debug logging: `export DEBUG_DELEGATION_HOOK=1` and check `/tmp/delegation_hook_debug.log`
- [ ] Check if TeamCreate is available by attempting it in a message

### Team Mode Failing Mid-Workflow

- [ ] Are teammates running? Check for active Task processes
- [ ] Is `team_config.json` valid? Check `cat .claude/state/team_config.json | jq .`
- [ ] Teammate stuck? Try `SendMessage` with shutdown_request
- [ ] Reset team state: `rm -f .claude/state/team_mode_active .claude/state/team_config.json`
- [ ] Fall back to subagent mode: re-run without `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`

### Python Validation Failing

- [ ] Is Ruff installed? Run `which ruff` or `uvx ruff --version`
- [ ] Is Pyright installed? Run `which pyright` or `npx pyright --version`
- [ ] Check specific error in PostToolUse output
- [ ] Skip validation if needed: `export CHECK_RUFF=0` or `export CHECK_PYRIGHT=0`

### StatusLine Not Updating

- [ ] Is statusline script installed? Check `ls -la ~/.claude/scripts/statusline.sh`
- [ ] Is script executable? Run `chmod +x ~/.claude/scripts/statusline.sh`
- [ ] Does state file exist? Check `ls -la .claude/state/active_delegations.json`
- [ ] Is JSON valid? Run `cat .claude/state/active_delegations.json | jq .`

---

## Common Patterns

### Basic Delegation

```bash
# Single task
/workflow-orchestrator:delegate Create a calculator.py with add and subtract functions

# Read-only question
/workflow-orchestrator:ask How does the authentication system work?
```

### Multi-Step Workflow

```bash
# Invoke the orchestrator via slash command — it loads commands/delegate.md on demand.
/workflow-orchestrator:delegate Create calculator.py with tests and verify they pass
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Run delegation
/workflow-orchestrator:delegate Create test.py

# Watch logs (separate terminal)
tail -f /tmp/delegation_hook_debug.log
```

### Emergency Bypass

```bash
# Disable delegation (emergency only)
export DELEGATION_HOOK_DISABLE=1

# Run direct commands
claude "Create file directly"

# Re-enable immediately
export DELEGATION_HOOK_DISABLE=0
```

### Reset All State

```bash
# Clear session registry
> .claude/state/delegated_sessions.txt

# Reset active delegations
echo '{"version":"2.0","execution_mode":"sequential","active_delegations":[]}' > .claude/state/active_delegations.json

# Remove task graph
rm -f .claude/state/active_task_graph.json

# Clear team state (if team mode was active)
rm -f .claude/state/team_mode_active .claude/state/team_config.json
```

### Monitor Workflow

```bash
# Watch status (separate terminal)
watch -n 1 ~/.claude/scripts/statusline.sh

# View current state
cat .claude/state/active_delegations.json | jq .

# Check recent events
tail -20 /tmp/claude_session_log.txt
```

---

## Complexity Scoring Quick Reference

### Formula

```
score = file_count*2 + lines/50 + concerns*1.5 + ext_deps + (arch_decisions ? 3 : 0)
```

### Tier Thresholds

| Tier | Score Range | Minimum Depth | Description |
|------|-------------|---------------|-------------|
| 1 | < 5 | 1 | Simple (utility, config) |
| 2 | 5-15 | 2 | Moderate (module, endpoint) |
| 3 | > 15 | 3 | Complex (feature, system) |

**Sonnet Override:** All tasks → Tier 3 (depth >= 3)

### Quick Estimates

| Task Type | Typical Score | Tier |
|-----------|---------------|------|
| "Create hello.py" | ~3 | 1 |
| "Create calculator with tests" | ~8 | 2 |
| "Implement auth endpoint with JWT" | ~12 | 2 |
| "Migrate monolith to microservices" | ~40+ | 3 |
| "Build notification system with SMS/email/push" | ~28 | 3 |

---

## Environment Variables Quick Reference

**Tasks API Configuration:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLAUDE_CODE_ENABLE_TASKS` | `true` | Enable Tasks API (set `false` to revert to TodoWrite) |
| `CLAUDE_CODE_TASK_LIST_ID` | Per-session | Share task list across sessions |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Not set | Disable async background tasks (reminders, cleanup) |

**Agent Teams:**

| Variable | Default | Enable | Purpose |
|----------|---------|--------|---------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `0` | `=1` | Enable dual-mode execution (team mode scoring and tools) |

**Debug & Control:**

| Variable | Default | Enable | Purpose |
|----------|---------|--------|---------|
| `DEBUG_DELEGATION_HOOK` | 0 | `=1` | Hook debug logging |
| `DELEGATION_HOOK_DISABLE` | 0 | `=1` | Emergency bypass |
| `CLAUDE_PROJECT_DIR` | `$PWD` | `=/path` | State file location |
| `CLAUDE_SCRATCHPAD_DIR` | - | `=/path` | Agent output scratchpad directory |
| `CLAUDE_MAX_CONCURRENT` | 8 | `=N` | Max parallel agents per batch |
| `CLAUDE_PARENT_SESSION_ID` | - | Auto | Subagent detection (hooks skip when set) |
| `CLAUDE_TOOL_INPUT` | - | Auto | Tool arguments JSON (preferred over CLAUDE_TOOL_ARGUMENTS) |
| `CHECK_RUFF` | 1 | `=0` | Skip Ruff validation |
| `CHECK_PYRIGHT` | 1 | `=0` | Skip Pyright validation |

---

## Team Mode Quick Reference

### Subagent vs Team Mode Comparison

| Aspect | Subagent Mode (Default) | Team Mode (Experimental) |
|--------|------------------------|--------------------------|
| Activation | Always available | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` + score >= 5 |
| Spawn mechanism | `Agent(...)` | `Agent(team_name="...", ...)` |
| Communication | None (isolated) | `SendMessage` (peer-to-peer) |
| Task list | Per-agent (isolated) | Shared across team |
| Context passing | Scratchpad files between waves | Scratchpad + real-time messaging |
| Coordination | Wave-based (lead controls) | Self-organizing (teammates coordinate) |
| Hook behavior | Full task graph validation | Graph validation bypassed |
| State files | Standard set | Standard + `team_mode_active` + `team_config.json` |
| Best for | Independent parallel tasks | Collaborative, iterative work |

### Communication Patterns

| Pattern | API | Cost | Use Case |
|---------|-----|------|----------|
| Point-to-point | `SendMessage(type: "message", recipient: "<name>")` | 1 delivery | Default. Status updates, questions, handoffs. |
| Broadcast | `SendMessage(type: "broadcast")` | N deliveries (1 per teammate) | Critical team-wide announcements only (e.g., "blocking issue found"). |

**Prefer point-to-point messaging.** Broadcast costs scale linearly with team size (N teammates = N separate message deliveries). Only broadcast when every teammate must act immediately.

### Team Mode Lifecycle Quick Reference

```
1. Plan mode checks if TeamCreate is available
2. If available → execution_mode: "team" in plan
3. Lead asks user for confirmation (AskUserQuestion)
4. TeamCreate(team_name="workflow-{timestamp}")
5. For each wave: Agent(team_name=..., subagent_type=...) per phase (NO run_in_background)
6. Wait for completion notifications
7. SendMessage shutdown_request to each teammate
8. TaskUpdate for completed phases
9. rm .claude/state/team_mode_active .claude/state/team_config.json
```

**Key difference from subagents:** Teammates spawned without `run_in_background: true` (they're persistent in the team session).

### Two Team Workflow Patterns

| Pattern | When | Plan Structure | Example |
|---------|------|----------------|---------|
| **Simple team** | Multi-perspective exploration | Single phase with `phase_type: "team"` + `teammates` array | "Analyze auth from security, performance, and UX angles" |
| **Complex team** | Collaborative implementation | Multiple phases across waves, `execution_mode: "team"` at plan level | "Build notification system collaboratively" |

### Team Mode Selection (ONE RULE)

**No scoring.** Tool availability is the only signal:

- **If TeamCreate tool available** → `execution_mode: "team"`
- **If TeamCreate tool NOT available** → `execution_mode: "subagent"`

Setting `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` makes TeamCreate available, enabling team mode. Without it, PreToolUse hook blocks TeamCreate (and thus team mode is not possible).

### Team Mode Commands

```bash
# Enable team mode capability
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Check team state
test -f .claude/state/team_mode_active && echo "Team mode ACTIVE" || echo "Team mode INACTIVE"
cat .claude/state/team_config.json | jq .

# Emergency cleanup (if team gets stuck)
rm -f .claude/state/team_mode_active .claude/state/team_config.json

# Disable team mode capability
unset CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
```

### Known Limitations

1. **No session resumption** -- `/resume` and `/rewind` do not restore in-process teammates. A resumed session starts without team state.
2. **Task status can lag** -- Teammates may fail to mark tasks completed, blocking dependents. The bridge pattern mitigates but does not eliminate this.
3. **Shutdown can be slow** -- Teammates finish their current request before honoring shutdown. Long-running agents delay cleanup.
4. **One team per session** -- Only one team can exist per Claude Code session. A second `TeamCreate` call is not supported.
5. **No nested teams** -- Teammates cannot spawn their own teams. Only the lead agent can create a team.
6. **Lead is fixed** -- No teammate promotion or leadership transfer. The lead is set at team creation and cannot change.
7. **Permissions set at spawn** -- All teammates inherit the lead's permission mode at creation. Per-teammate permissions are not supported.
8. **Split panes require tmux or iTerm2** -- Split-pane visualization does not work in VS Code terminal, Windows Terminal, or Ghostty.

---

## Related Documentation

- [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md) - Comprehensive design documentation (includes Dual-Mode Execution Philosophy)
- [Hook Debugging Guide](./hook-debugging.md) - Detailed hook troubleshooting
- [Environment Variables](./environment-variables.md) - Full configuration reference
- [StatusLine System](./statusline-system.md) - Status display documentation
- [Python Coding Standards](./python-coding-standards.md) - Code quality requirements
- [Main Documentation](../CLAUDE.md) - Project overview
