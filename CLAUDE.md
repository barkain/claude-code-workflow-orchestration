# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Delegation Policy (Soft Enforcement)

The framework nudges via stderr when the main agent uses work-doing tools (`Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `MultiEdit`, `NotebookEdit`) directly. **Nudges never block.** They escalate by per-turn violation count: silent → short hint → warning → strong reminder. The counter resets each turn and zeros when `/workflow-orchestrator:delegate` runs.

The expected path for any multi-step or work-shaped request is:

```
/workflow-orchestrator:delegate <task description>
```

Subagents are immune (they're executing a delegation). New tools added by Claude Code never trigger nudges — only the 8 stable work primitives are tracked.

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
/workflow-orchestrator:delegate <task>   # Plan and execute task via native plan mode
/workflow-orchestrator:ask <question>    # Read-only question answering (forked context)
/workflow-orchestrator:add-statusline    # Enable workflow status display
```

**Installation:**
- Plugin: `claude plugin install workflow-orchestrator@barkain-plugins`
- Manual: `./install.sh [--scope=user|project]`

In plugin mode, all commands and agent names use the `workflow-orchestrator:` prefix.

---

## Architecture Overview

### Execution Flow

**Token overhead:** Conditional injection (stub ~200 tokens on startup, full ~7.5K tokens on first delegation, optional token-efficient guide ~1.9K) + per-agent delegation (~350 tokens)

```
User prompt
  → UserPromptSubmit hook (clear state, record turn timestamp, clear team state)
  → SessionStart hooks (inject stub orchestrator + output style + token efficiency)
    [Stub version provides just enough system direction, avoiding unnecessary tokens]
  → Task detection: if multi-step connectors found, enters native plan mode (EnterPlanMode)
  → plan mode: injects full workflow_orchestrator, explores codebase, decomposes, assigns agents, creates tasks via TaskCreate
  → plan mode: evaluates execution_mode (subagent vs team via TeamCreate tool availability)
  → plan mode: exits via ExitPlanMode (requires lead approval)
  → PostToolUse hook (remind_skill_continuation.py): creates workflow_continuation_needed.json on ExitPlanMode
  → After ExitPlanMode approval, main agent continues to Stage 1
  → Main agent: Stage 1 — parses execution plan JSON, renders dependency graph
  → SUBAGENT MODE (default):
    → For each wave: spawn agents via Agent tool (run_in_background: true)
    → Agents write to $CLAUDE_SCRATCHPAD_DIR, return DONE|{path}
    → SubagentStop hooks: remind task update, suggest verification
    → Main agent: TaskUpdate to mark completed, proceed to next wave
  → TEAM MODE (when TeamCreate tool is available):
    → Create .claude/state/team_mode_active + team_config.json
    → TeamCreate(team_name=...), then Agent(team_name=...) for each teammate with agent configs
    → Create shared tasks with dependencies, bridge to framework Tasks API
    → Teammates self-claim tasks, self-coordinate via messaging
    → Lead syncs team completions to TaskUpdate (bridge pattern)
    → Cleanup team state on completion
  → Stop hook: calculate turn duration, quality analysis
```

### Hook System (6 lifecycle events, 14 hooks)

| Event | Scripts | Purpose |
|-------|---------|---------|
| **PreToolUse** (`*`, `Bash`) | `validate_task_graph_compliance.py` (advisory), `require_delegation.py` (adaptive nudge), `token_rewrite_hook.py` (Bash only) | Hint on out-of-order Agent/Task spawns; emit per-turn escalating delegation nudge (silent → strong); rewrite Bash for token-efficient output |
| **PostToolUse** | `python_posttooluse_hook.py` (Edit/Write/MultiEdit, **blocking**), `remind_skill_continuation.py` (ExitPlanMode\|Skill\|SlashCommand), `validate_task_graph_depth.py` (advisory) + `remind_todo_after_task.py` (Agent/Task) | Python validation (Ruff, Pyright, security — only hard-blocking hook); workflow continuation + zero violations counter on `/workflow-orchestrator:delegate`; depth hint; task reminders |
| **UserPromptSubmit** | `clear-delegation-sessions.py` | Reset per-turn state (timestamp, violations counter), clear team state, rotate logs |
| **SessionStart** (`startup\|resume\|clear\|compact`) | `inject_all.py` | Consolidated injection (orchestrator stub + token efficiency). Output style is loaded natively from plugin.json's `outputStyles` field |
| **SubagentStop** (`*`) | `remind_todo_update.py` (async), `trigger_verification.py` | Remind to update tasks, suggest verification |
| **Stop** | `python_stop_hook.py` | Turn duration, workflow continuation, quality analysis |

Hook config source of truth: `hooks/plugin-hooks.json` (not settings.json). All hooks are Python for cross-platform compatibility (Windows/macOS/Linux).

### Soft Enforcement (Adaptive Nudges)

There is no allowlist. `require_delegation.py` tracks per-turn direct work-tool calls and writes a stderr message that escalates by count:

| Violations | Message | Tokens |
|---|---|---|
| 0 | (silent) | 0 |
| 1 | `delegate?` | ~2 |
| 2 | `nudge: use /workflow-orchestrator:delegate for multi-step work` | ~12 |
| 3–4 | `WARNING: N direct tool calls bypassing delegation. Use /workflow-orchestrator:delegate <task>.` | ~25 |
| 5+ | Strong reminder explaining what's being lost | ~55 |

Tracked tools (the only ones that count as violations): `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `MultiEdit`, `NotebookEdit`. These 8 stable primitives are the only ones monitored. New Claude Code tools never trigger nudges.

The counter:
- Resets each turn (`UserPromptSubmit`)
- Zeros when `/workflow-orchestrator:delegate` runs (slate clean — model chose the right path)
- Is bypassed entirely for subagents (they're executing a delegation; `CLAUDE_PARENT_SESSION_ID` / `CLAUDE_AGENT_ID` set)
- Is bypassed when `.claude/state/delegation_active` exists (delegation already in progress)

The only hook that still hard-blocks is `python_posttooluse_hook.py` (Ruff/Pyright on edited Python files — stable surface, fix-forward UX).

**Note:** The `task-planner` and `breadth-reader` skills have been removed. Planning and orchestration are provided by native plan mode (EnterPlanMode/ExitPlanMode). Read-only breadth tasks are handled by spawning parallel Explore agents or the codebase-context-analyzer directly.

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

Multi-agent execution is mandatory — all plans produce ≥2 subtasks. Default is team mode when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, otherwise parallel subagents.

**Subagent mode**: Current pipeline. Main agent spawns Agent tool instances per wave. Agents return `DONE|{path}`. Context-efficient, used when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is not set.

**Team mode** (experimental): Uses Claude Code's Agent Teams feature. Lead agent calls `TeamCreate(team_name=...)`, then spawns teammates via `Agent(team_name=..., subagent_type=..., prompt=...)`. The `team_name` parameter makes Agent invocations teammates (shared context, `SendMessage`) vs isolated subagents. Teammates self-claim tasks, communicate peer-to-peer. Bridge pattern syncs team task completions to framework Tasks API. Teammates use `SendMessage(type: "message")` for point-to-point communication and `SendMessage(type: "broadcast")` for team-wide announcements. Broadcast sends N separate messages (one per teammate) so prefer point-to-point messaging; reserve broadcast for critical announcements only.

Two team workflow patterns:
- **Team mode (simple):** Single AGENT TEAM phase with `phase_type: "team"` and `teammates` array -- used for multi-perspective exploration (e.g., "explore from different angles")
- **Team mode (complex):** Multiple individual phases across waves, all executed as teammates via `Agent(team_name=...)` -- used for collaborative implementation (e.g., "implement project, tasks should be collaborative"). The plan has `execution_mode: "team"` at the top level; no individual phase needs `phase_type: "team"`

**Mode selection** is based on ONE RULE (detected during plan mode):
- **If TeamCreate tool is available** (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 is set): `execution_mode: "team"`
- **If TeamCreate tool is not available** (env var not set): `execution_mode: "subagent"` (≥2 subtasks mandatory)

**When team mode is active:**
- `validate_task_graph_compliance.py` hook is bypassed (team handles dependencies)
- Agent Teams tools are added to the allowlist (TeamCreate, SendMessage; teammates via Agent with team_name param)
- Agents use conditional COMMUNICATION MODE (teammate messaging vs `DONE|{path}`)
- State files: `.claude/state/team_mode_active`, `.claude/state/team_config.json`

Agent selection uses keyword matching (≥2 matches threshold, highest count wins). Falls back to general-purpose if 0-1 matches. See `commands/delegate.md` (Available Specialized Agents section) for keyword lists.

Agent config format: YAML frontmatter (`name`, `description`, optional `tools`/`model`/`color`) + markdown system prompt body. All agents enforce `DONE|{output_file}` return format. Custom agent instructions include:
- Return format must be exactly `DONE|{output_file_path}` (no summaries or explanations)
- Write directly to output file using Write tool (do not delegate writing)
- If Write is blocked, report error and stop (do not retry)

### State Files (Runtime)

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `.claude/state/delegation_violations.json` | Per-turn nudge counter (`{violations, delegations, turn_id}`) | Reset per user prompt; zeroed on `/workflow-orchestrator:delegate` |
| `.claude/state/delegation_active` | Active-delegation flag (suppresses nudges) | Per-delegation |
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
| `DEBUG_DELEGATION_HOOK` | `0` | Enable hook debug logging to `/tmp/delegation_hook_debug.log` |
| `CLAUDE_MAX_CONCURRENT` | `8` | Max parallel agents per batch |
| `CHECK_RUFF` | `1` | Skip Ruff validation (`0` to disable) |
| `CHECK_PYRIGHT` | `1` | Skip Pyright validation (`0` to disable) |
| `CLAUDE_SKIP_PYTHON_VALIDATION` | `0` | Skip all Python validation (`1` to disable) |
| `CLAUDE_PARENT_SESSION_ID` | Not set | Auto-set for subagents (bypasses hooks) |
| `CLAUDE_PLUGIN_ROOT` | Not set | Set by plugin system for path resolution |
| `CLAUDE_SCRATCHPAD_DIR` | Per-session | Session-isolated temp dir for agent output |
| `CLAUDE_PROJECT_DIR` | `$PWD` | State directory base path |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `0` | Enable Agent Teams (TeamCreate tool availability and team mode scoring; `1` to enable) |
| `CLAUDE_CODE_ENABLE_TASKS` | `true` | Set `false` to revert to TodoWrite |
| `CLAUDE_CODE_TASK_LIST_ID` | Per-session | Share task list across sessions |
| `CLAUDE_TOKEN_EFFICIENCY` | `1` | Enable token-efficient CLI output compression (`0` to disable) |

---

## Token-Efficient CLI Usage

Minimize command output to reduce context consumption. Enabled by default (`CLAUDE_TOKEN_EFFICIENCY=1`).

**Multi-layer approach:**
1. **Behavioral guidance** (`system-prompts/token_efficient_cli.md`): Injected via SessionStart, teaches compact flag usage (e.g., `git status -sb`, `pytest -q --tb=short`)
2. **Output compression** (`hooks/compact_run.py`): PreToolUse hook rewrites matching Bash commands through `compact_run.py`, which compresses git/test/log output post-execution
3. **cd && pattern handling**: Hooks support chained commands with `cd && command` pattern for working directory preservation in compressed output
4. **Extended language support**: Rewrite hook supports eslint, next, tsc build tools in addition to git/test families
5. **Partial file reads**: Use Read tool with `offset` and `limit` parameters for files >200 lines to avoid loading entire file contents into context
6. **Compressed error messages**: Delegation error messages are optimized for minimal token consumption (use logging, never print statements)

**Supported command families:** git (push/pull/commit/etc), pytest, cargo test, npm/pnpm/yarn/bun test, npx (vitest/jest/mocha/playwright), go test, make test/check, docker/kubectl logs, eslint, next, tsc

Disable: `export CLAUDE_TOKEN_EFFICIENCY=0`

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
cat .claude/state/delegation_violations.json   # current per-turn nudge counter
ls .claude/state/delegation_active 2>/dev/null  # delegation in progress?
```

**Multi-step not detected:**
Ensure the SessionStart hook is installed (`hooks/SessionStart/inject_all.py`) so `orchestrator_stub.md` is injected and the main agent knows to route multi-step work through `/workflow-orchestrator:delegate`. Use connectors in prompts: "and then", "with", "including".

**TeamCreate blocked:**
```bash
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS  # Check if set to "1"
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
The PreToolUse hook blocks all team tools (`TeamCreate`, `SendMessage`, pattern `*team*`/`*teammate*`) unless this env var is set. The hook auto-creates `.claude/state/team_mode_active` when the env var is "1" and a team tool is invoked.

**Team mode not activating despite keywords:**
Team mode is activated by tool availability detection during plan mode. Ensure `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set before running a workflow that should use team mode. The planning phase checks if `TeamCreate` tool is available. If the env var is not set, `TeamCreate` is blocked by PreToolUse hook, so plan mode always selects `"subagent"` mode (with ≥2 subtasks mandatory).

**Team state files stale after crash:**
```bash
rm -f .claude/state/team_mode_active .claude/state/team_config.json
```
These are normally cleaned up by the UserPromptSubmit hook on each new user prompt. If a session crashed mid-team-workflow, manually remove them.

**One team per session:**
Only one team can exist in a Claude Code session. Do not call `TeamCreate` a second time. If you need a fresh team, start a new session.

**No nested teams:**
Teammates cannot create their own teams. `TeamCreate` is restricted to the lead agent. If a teammate needs sub-coordination, use subagent `Agent()` calls (without `team_name`) instead.

**Shutdown can be slow:**
Teammates finish their current request before honoring a `shutdown_request`. For long-running agents, expect a delay. If a teammate appears stuck, check its task status and send another `shutdown_request` after the current request completes.

See `docs/` directory for detailed architecture docs, hook debugging guide, and validation schemas.
