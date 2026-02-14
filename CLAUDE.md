# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Critical: Delegation Policy

**MANDATORY IMMEDIATE DELEGATION ON TOOL BLOCK**

When ANY tool is blocked by the delegation policy hook:

1. **DO NOT try alternative approaches** - just delegate immediately
2. **IMMEDIATELY use `/delegate <task>`** on first tool block
3. **The entire user request must be delegated**, not just the blocked tool

### Recognition Pattern

```
Error: PreToolUse:* hook error: [...] Tool blocked by delegation policy
Tool: <ToolName>

STOP: Do NOT try alternative tools.
REQUIRED: Use /delegate command immediately:
   /delegate <full task description>
```

First tool block = immediate delegation. Don't try alternatives, don't explain — just delegate.

---

## Prerequisites

- **uv** - Python package manager (required for `uvx`, `uv run`)
- **bun** - JavaScript runtime (for ccusage cost tracking in statusline)
- **jq** - JSON processor (optional, for advanced features)

No `pyproject.toml` exists — all scripts use `uv run --no-project --script` mode.

---

## Build, Lint, and Test Commands

```bash
uvx ruff format .                # Format code (auto-fix)
uvx ruff check --no-fix .       # Lint code (check only)
uvx pyright .                    # Type checking
uvx deadcode hooks/ scripts/    # Dead code detection
```

The PostToolUse hook enforces a specific ruff rule subset on edited Python files:
```bash
uvx ruff check --select F,E711,E712,UP006,UP007,UP035,UP037,T201,S <file>
```

CI workflow exists (`.github/workflows/ci.yml`) but tests are currently disabled/placeholder.

---

## Available Commands

```bash
/delegate <task>           # Plan and execute task via native plan mode
/ask <question>            # Read-only question answering (forked context)
/bypass                    # Toggle delegation enforcement on/off (persists until toggled)
/add-statusline            # Enable workflow status display
/breadth-reader <prompt>   # Read-only breadth tasks (explore, review, summarize)
```

**Installation:**
- Plugin: `claude plugin install workflow-orchestrator@barkain-plugins`
- Manual: `./install.sh [--scope=user|project]`

In plugin mode, agent/skill names use prefix `workflow-orchestrator:` (e.g., `workflow-orchestrator:task-completion-verifier`).

---

## Architecture Overview

### Execution Flow

```
User prompt
  → UserPromptSubmit hook (clear state, record turn timestamp, clear team state)
  → SessionStart hooks (inject workflow_orchestrator.md + output style)
  → workflow_orchestrator detects multi-step → enters native plan mode (EnterPlanMode)
  → plan mode: main agent explores codebase, decomposes, assigns agents, creates tasks via TaskCreate
  → plan mode: evaluates execution_mode (subagent vs team via team_mode_score)
  → plan mode: exits via ExitPlanMode (requires lead approval)
  → PostToolUse hook (remind_skill_continuation.py): creates workflow_continuation_needed.json on ExitPlanMode
  → After ExitPlanMode approval, main agent continues to Stage 1
  → Main agent: Stage 1 — parses execution plan JSON, renders dependency graph
  → SUBAGENT MODE (default):
    → For each wave: spawn agents via Task tool (run_in_background: true)
    → Agents write to $CLAUDE_SCRATCHPAD_DIR, return DONE|{path}
    → SubagentStop hooks: remind task update, suggest verification
    → Main agent: TaskUpdate to mark completed, proceed to next wave
  → TEAM MODE (experimental, CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1):
    → Create .claude/state/team_mode_active + team_config.json
    → TeamCreate(team_name=...), then Task(team_name=...) for each teammate with agent configs
    → Create shared tasks with dependencies, bridge to framework Tasks API
    → Teammates self-claim tasks, self-coordinate via messaging
    → Lead syncs team completions to TaskUpdate (bridge pattern)
    → Cleanup team state on completion
  → Stop hook: calculate turn duration, quality analysis
```

### Hook System (6 lifecycle events, 12 scripts)

| Event | Scripts | Purpose |
|-------|---------|---------|
| **PreToolUse** (`*`) | `require_delegation.py`, `validate_task_graph_compliance.py` | Block non-allowed tools; validate Task invocations against active task graph |
| **PostToolUse** | `python_posttooluse_hook.py` (Edit/Write/MultiEdit), `remind_skill_continuation.py` (ExitPlanMode\|Skill\|SlashCommand), `validate_task_graph_depth.py` + `remind_todo_after_task.py` (Task) | Python validation (Ruff, Pyright, security), workflow continuation state (triggers on ExitPlanMode for plan mode flows), depth-3 enforcement, task reminders |
| **UserPromptSubmit** | `clear-delegation-sessions.py` | Clear delegation state, record turn start timestamp, clear team state (`team_mode_active`, `team_config.json`), rotate logs |
| **SessionStart** (`startup\|resume\|clear\|compact`) | `inject_workflow_orchestrator.py`, `inject-output-style.py` | Inject system prompt + output style |
| **SubagentStop** (`*`) | `remind_todo_update.py` (async), `trigger_verification.py` | Remind to update tasks, suggest verification |
| **Stop** | `python_stop_hook.py` | Turn duration, workflow continuation (block stop + inject "continue"), quality analysis |

Hook config source of truth: `hooks/plugin-hooks.json` (not settings.json). All hooks are Python for cross-platform compatibility (Windows/macOS/Linux).

### Tool Allowlist

Main agent can only use: `AskUserQuestion`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`, `Skill`, `SlashCommand`, `Task`, `SubagentTask`, `AgentTask`, `EnterPlanMode`, `ExitPlanMode`

Special cases:
- `Write` tool allowed for temp/scratchpad paths only (`/tmp/`, `/private/tmp/`, `/var/folders/`)
- `TaskOutput` is **prohibited** (context exhaustion: ~20K tokens per agent)
- `TaskList` polling loops are **prohibited** (use completion notifications instead)

**Agent Teams tools** (conditional, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):
- Explicit: `TeamCreate`, `SendMessage`
- Teammates are spawned via `Task` tool with `team_name` parameter (Task is already in the main allowlist)
- Pattern match: Any tool name containing `"team"` or `"teammate"` (case-insensitive) as safety net

### Bypass Mechanisms

| Mechanism | How | Scope |
|-----------|-----|-------|
| Env var | `DELEGATION_HOOK_DISABLE=1` | Session-wide |
| `/bypass` command | Creates `.claude/state/delegation_disabled` | Persists until toggled |
| Subagent auto-bypass | `CLAUDE_PARENT_SESSION_ID` set | Automatic for subagents |
| Delegation active flag | `.claude/state/delegation_active` created on Skill/Task use | Per-delegation |

### Skills (forked context)

- **task-planner** (`skills/task-planner/SKILL.md`): Legacy planning skill, retained for reference/backward compatibility. The core planning logic (complexity scoring, tier classification, agent assignment, wave scheduling, task creation) has been absorbed into `system-prompts/workflow_orchestrator.md` and now executes as native plan mode (EnterPlanMode/ExitPlanMode) directly in the main agent context rather than a forked skill context.
- **breadth-reader** (`skills/breadth-reader/SKILL.md`): Lightweight read-only breadth tasks. Spawns `Explore` subagents (Haiku). Returns summary only.

### Specialized Agents (8)

| Agent | Domain |
|-------|--------|
| codebase-context-analyzer | Read-only code exploration, architecture analysis |
| code-reviewer | Code review, quality assessment |
| code-cleanup-optimizer | Refactoring, technical debt |
| devops-experience-architect | Infrastructure, CI/CD, deployment |
| task-completion-verifier | Testing, QA, validation |
| tech-lead-architect | Solution design, architecture decisions |
| documentation-expert | Documentation creation/maintenance |
| dependency-manager | Package management (Python/UV focused) |

All 8 agents include a conditional COMMUNICATION MODE section: when running as a teammate (Agent Teams), they send messages via `SendMessage`; when running as an isolated subagent, they return `DONE|{output_file}`.

### Dual-Mode Execution (Subagent vs Team)

The framework supports two execution modes, selected at planning time during native plan mode:

**Subagent mode** (default): Current pipeline. Main agent spawns Task tool instances per wave. Agents return `DONE|{path}`. Context-efficient, optimal for most workflows.

**Team mode** (experimental): Uses Claude Code's Agent Teams feature. Lead agent calls `TeamCreate(team_name=...)`, then spawns teammates via `Task(team_name=..., subagent_type=..., prompt=...)`. The `team_name` parameter makes Task invocations teammates (shared context, `SendMessage`) vs isolated subagents. Teammates self-claim tasks, communicate peer-to-peer. Bridge pattern syncs team task completions to framework Tasks API. Teammates use `SendMessage(type: "message")` for point-to-point communication and `SendMessage(type: "broadcast")` for team-wide announcements. Broadcast sends N separate messages (one per teammate) so prefer point-to-point messaging; reserve broadcast for critical announcements only.

Two team workflow patterns:
- **Team mode (simple):** Single AGENT TEAM phase with `phase_type: "team"` and `teammates` array -- used for multi-perspective exploration (e.g., "explore from different angles")
- **Team mode (complex):** Multiple individual phases across waves, all executed as teammates via `Task(team_name=...)` -- used for collaborative implementation (e.g., "implement project, tasks should be collaborative"). The plan has `execution_mode: "team"` at the top level; no individual phase needs `phase_type: "team"`

**Mode selection** uses `team_mode_score` (calculated during plan mode):
- Phase count >8: +2, Tier 3 complexity: +2, cross-phase data flow: +3
- Review-fix cycles: +3, iterative refinement: +2, user keyword "collaborate"/"team": +5
- Breadth task: -5, phase count <=3: -3
- Score >=5 with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` = team mode

**When team mode is active:**
- `validate_task_graph_compliance.py` hook is bypassed (team handles dependencies)
- Agent Teams tools are added to the allowlist (TeamCreate, SendMessage; teammates via Task with team_name param)
- Agents use conditional COMMUNICATION MODE (teammate messaging vs `DONE|{path}`)
- State files: `.claude/state/team_mode_active`, `.claude/state/team_config.json`

Agent selection uses keyword matching (≥2 matches threshold, highest count wins). Falls back to general-purpose if 0-1 matches. See `system-prompts/workflow_orchestrator.md` for keyword lists.

Agent config format: YAML frontmatter (`name`, `description`, optional `tools`/`model`/`color`) + markdown system prompt body. All agents enforce `DONE|{output_file}` return format.

### State Files (Runtime)

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `.claude/state/delegated_sessions.txt` | Session registry | Cleared per user prompt |
| `.claude/state/delegation_active` | Subagent session flag | Per-delegation |
| `.claude/state/delegation_disabled` | Bypass flag | Until `/bypass` toggle |
| `.claude/state/active_delegations.json` | Parallel wave tracking | Per-workflow |
| `.claude/state/active_task_graph.json` | Task graph for validation | Per-workflow |
| `.claude/state/workflow_continuation_needed.json` | Signal stop hook to auto-continue | Per-plan-mode exit (ExitPlanMode) |
| `.claude/state/turn_start_timestamp.txt` | Turn timing start | Per-user-prompt |
| `.claude/state/last_turn_duration.txt` | Formatted duration | Per-turn |
| `.claude/state/turn_durations.json` | Last 10 durations (sparkline) | Rolling |
| `.claude/state/team_mode_active` | Signals hooks that Agent Teams mode is active | Auto-created by PreToolUse on first team tool use or during plan mode; cleared by UserPromptSubmit or Stage 1 cleanup |
| `.claude/state/team_config.json` | Active team configuration (name, teammates, role mappings) | Created at team bootstrap, cleared by UserPromptSubmit |
| `.claude/state/validation/` | Validation state + gate log | Auto-cleaned after 24h |

### Statusline

`scripts/statusline.py` provides context usage (progress bar), session cost (via ccusage/bun), git branch, turn duration with sparkline, and Claude version. Configured via `settings.json` `statusLine` field.

---

## Python Coding Standards

- Python 3.12+ with modern syntax: `list[str]` not `List[str]`, `str | None` not `Optional[str]`
- No print statements — use logging (Ruff T201 rule enforced)
- All scripts include Windows UTF-8 forcing pattern and `sys.exit(main())` entry
- Cross-platform temp paths via `Path(tempfile.gettempdir())`
- Hook return codes: 0 = allow/success, 2 = block (PreToolUse), 1 = error
- Enforced by: Ruff (linting/formatting), Pyright (type checking)

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DELEGATION_HOOK_DISABLE` | `0` | Emergency bypass (`1` to disable enforcement) |
| `DEBUG_DELEGATION_HOOK` | `0` | Enable hook debug logging to `/tmp/delegation_hook_debug.log` |
| `CLAUDE_MAX_CONCURRENT` | `8` | Max parallel agents per batch |
| `CHECK_RUFF` | `1` | Skip Ruff validation (`0` to disable) |
| `CHECK_PYRIGHT` | `1` | Skip Pyright validation (`0` to disable) |
| `CLAUDE_SKIP_PYTHON_VALIDATION` | `0` | Skip all Python validation (`1` to disable) |
| `CLAUDE_PARENT_SESSION_ID` | Not set | Auto-set for subagents (bypasses hooks) |
| `CLAUDE_PLUGIN_ROOT` | Not set | Set by plugin system for path resolution |
| `CLAUDE_SCRATCHPAD_DIR` | Per-session | Session-isolated temp dir for agent output |
| `CLAUDE_PROJECT_DIR` | `$PWD` | State directory base path |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `0` | Enable Agent Teams dual-mode (`1` to enable team mode scoring and tools) |
| `CLAUDE_CODE_ENABLE_TASKS` | `true` | Set `false` to revert to TodoWrite |
| `CLAUDE_CODE_TASK_LIST_ID` | Per-session | Share task list across sessions |

---

## Troubleshooting

**Tools blocked but delegation fails:**
```bash
ls ~/.claude/hooks/PreToolUse/        # Verify hooks installed
cp -r agents hooks ~/.claude/         # Reinstall if missing
```

**Debug hook behavior:**
```bash
export DEBUG_DELEGATION_HOOK=1
tail -f /tmp/delegation_hook_debug.log
```

**Check delegation state:**
```bash
cat .claude/state/delegated_sessions.txt
cat .claude/state/delegation_disabled    # bypass active?
```

**Multi-step not detected:**
Ensure SessionStart hooks are installed (inject_workflow_orchestrator.py) so that workflow_orchestrator.md is injected and native plan mode (EnterPlanMode/ExitPlanMode) is available. Use connectors in prompts: "and then", "with", "including".

**TeamCreate blocked:**
```bash
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS  # Must be "1"
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
The PreToolUse hook blocks all team tools (`TeamCreate`, `SendMessage`, pattern `*team*`/`*teammate*`) unless this env var is set. The hook prints a specific error message indicating the env var is missing.

**Team mode not activating despite keywords:**
Ensure `team_mode_score >= 5`. Simple tasks (<=3 phases) get -3, breadth tasks get -5. Add explicit keywords like "collaborate" or "team" (+5) to trigger team mode. Check `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set -- without it, plan mode always selects `"subagent"` mode regardless of score.

**Team state files stale after crash:**
```bash
rm -f .claude/state/team_mode_active .claude/state/team_config.json
```
These are normally cleaned up by the UserPromptSubmit hook on each new user prompt. If a session crashed mid-team-workflow, manually remove them.

**One team per session:**
Only one team can exist in a Claude Code session. Do not call `TeamCreate` a second time. If you need a fresh team, start a new session.

**No nested teams:**
Teammates cannot create their own teams. `TeamCreate` is restricted to the lead agent. If a teammate needs sub-coordination, use subagent `Task()` calls (without `team_name`) instead.

**Shutdown can be slow:**
Teammates finish their current request before honoring a `shutdown_request`. For long-running agents, expect a delay. If a teammate appears stuck, check its task status and send another `shutdown_request` after the current request completes.

See `docs/` directory for detailed architecture docs, hook debugging guide, and validation schemas.
