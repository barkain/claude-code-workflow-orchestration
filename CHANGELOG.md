# Changelog

All notable changes to this project will be documented in this file.

## [1.15.2] - 2026-04-04

### Fixed
- **$0.00 cost display**: Use `cost.total_cost_usd` from stdin JSON for real-time session cost; daily cost already uses JSONL self-calculation (no ccusage dependency)
- **Delegation hook subagent deadlock**: Expanded subagent bypass to check `CLAUDE_AGENT_ID` and `CLAUDE_SCRATCHPAD_DIR` in addition to `CLAUDE_PARENT_SESSION_ID`; added redundant safety net inside `main()`; normalized `CLAUDE_PROJECT_DIR` path resolution with `Path.resolve()`

## [1.15.1] - 2026-04-04

### Fixed
- **Worktree directory/branch detection**: Statusline now uses `cwd` from Claude Code's stdin JSON instead of `os.getcwd()`, correctly reflecting the working directory when Claude switches to a git worktree
- **stdin cwd type validation**: Added type check for stdin `cwd` field to handle unexpected input gracefully

## [1.15.0] - 2026-04-03

### Added
- **5h/weekly usage percentages**: Display real Anthropic plan usage limits in statusline, read directly from Claude Code's `rate_limits` JSON input (zero API calls)
- **Responsive statusline layout**: Terminal width detection with 4-tier progressive compaction for narrow/split terminals
- **Color-coded usage thresholds**: Green (<50%), yellow (50-75%), red (>=75%) for usage percentages

### Changed
- **Context bar shortened**: Reduced from 20 to 10 characters for better space utilization
- **Directory/branch truncation**: Dir max 25 chars, branch max 20 chars with ellipsis truncation
- **Row 2 priority layout**: Context bar + usage % (always shown) > cost (>=80 cols) > duration (>=60 cols)

### Removed
- **Sparkline/cycle time graph**: Removed `generate_sparkline()` visualization, duration text preserved
- **Session cost display**: Removed `🎯 $X.XX` from statusline row 2
- **OAuth usage API code**: Replaced with direct stdin JSON reading (API is permanently rate-limited)

### Fixed
- **Narrow terminal handling**: Width detection no longer forces small values to 120, allowing compact layouts to trigger
- **Double session file read**: `calculate_context_usage()` returns raw percentage for reuse in minimal layout
- **Usage color boundaries**: Corrected to `>=50` yellow and `>=75` red (was strict greater-than)

## [1.14.0] - 2026-03-24

### Added
- **Madrox plugin in marketplace**: Added [Madrox](https://github.com/barkain/madrox) MCP server to the `barkain-plugins` marketplace, enabling parallel Claude CLI worker orchestration with a real-time dashboard

## [1.13.0] - 2026-03-21

### Added
- **Token-efficient CLI output compression**: Two-layer system with behavioral guidance (SessionStart injection) and output compression (PreToolUse rewrite hook through `compact_run.py`)
- **Cross-platform `compact_run.py`**: Python output compressor replacing bash script, supports git, pytest, cargo, npm/pnpm/yarn/bun, npx (vitest/jest/mocha/playwright/eslint/next/tsc), go, make, docker/kubectl
- **Conditional orchestrator injection**: 40-line stub (~200 tokens) on session start, full orchestrator (~5.5K tokens) loads on-demand via `/delegate` — 55% overhead reduction
- **Agent Teams enforcement**: Team mode as primary execution mode when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set, with TeamCreate tool availability detection
- **`_npx_safe()` guard**: Prevents wrapping long-running commands (`next dev/start/build`, `tsc --watch`) through compact_run
- **Comprehensive test suite**: 205 tests covering compact_run, token_rewrite_hook, inject_token_efficiency, and integration scenarios
- **Claude Code Review CI workflow**: GitHub Actions workflow for automated PR review via Claude Code Action

### Changed
- **Slimmed workflow orchestrator**: 49% reduction (1065→545 lines) with conditional section loading
- **Agent definitions deduplicated**: 47% reduction (640→339 lines) across all 8 agents with CLI efficiency rules and DONE|{output_file} enforcement
- **Output style updated**: Mandatory filler reduction rules (post-edit brevity, no restatement, table threshold ≥4, wave-level reporting)
- **Delegation error messages compressed**: Single-line format using logging instead of print
- **`/delegate` command**: Expanded allowed-tools (12 tools), embeds full orchestrator for on-demand loading

### Removed
- **`skills/task-planner/`**: Deprecated planning skill deleted — all planning via native plan mode (EnterPlanMode/ExitPlanMode)
- **`hooks/compact-run.sh`**: Replaced by cross-platform `hooks/compact_run.py`

### Fixed
- **Team mode activation**: Changed from env var Bash check (blocked by delegation hook) to TeamCreate tool availability detection
- **`cd && command` pattern**: Rewrite hook extracts command after `cd <path> &&` for proper wrapping
- **Exit code handling**: Uncaught exceptions in require_delegation.py now exit with code 1 (error) instead of 0 (allow)
- **PEP 723 metadata**: Added to all scripts run via `uv run --script`

## [1.12.0] - 2026-03-14

### Added
- **Token-efficient CLI usage**: Behavioral guidance injection (`token_efficient_cli.md`) and output compression hook (`compact_run.py`) for reduced context consumption
- **Mandatory multi-agent execution**: All plans now produce 2+ subtasks; single-subtask plans prohibited
- **Token efficiency rules**: Enforced across all 8 agent definitions
- **`inject_token_efficiency.py`** SessionStart hook and **`token_rewrite_hook.py`** PreToolUse hook
- **Test suite**: 196 tests covering compact_run, token_rewrite_hook, inject_token_efficiency, and integration

### Changed
- **Statusline reorganized**: Static info on row 1, dynamic metrics on row 2
- **Removed `alwaysThinkingEnabled`** from settings
- **Windows `.exe` command normalization** for cross-platform support
- **Configurable subprocess timeout**: `COMPACT_RUN_TIMEOUT` (default 120s)

## [1.11.1] - 2026-03-10

### Fixed
- **ToolSearch allowlist**: Added `ToolSearch` to delegation policy allowlist to prevent deadlock when fetching deferred tool schemas
- **Delegation error message**: Fixed to use correct skill name (`/workflow-orchestrator:delegate` instead of `/delegate`)
- **CI review workflow**: Disabled delegation hook to allow Claude Code review action to function
- **Documentation**: Updated allowlists in CLAUDE.md, ARCHITECTURE_QUICK_REFERENCE.md, hook-debugging.md, and ARCHITECTURE_PHILOSOPHY.md to include ToolSearch

## [1.11.0] - 2026-02-28

### Changed
- **Task tool renamed to Agent tool**: Updated entire framework for Claude Code v2.1.63 rename of `Task` to `Agent` for spawning subagents
- All documentation uses `Agent(...)` as primary invocation form
- Python hooks accept both `"Agent"` and `"Task"` tool names
- `plugin-hooks.json` matcher uses `Agent|Task` regex pattern
- 8 agent config files updated to reference `(Agent tool)`
- Allowlist includes both `Agent` and `Task` for backwards compatibility

## [1.10.1] - 2026-02-14

### Fixed
- **Tilde expansion in install.sh**: Use `$HOME` instead of `~` in `path_prefix` — single-quoted `~` prevented tilde expansion, causing Python hook commands to receive literal `~/.claude/...` paths that couldn't be resolved

## [1.10.0] - 2026-02-14

### Added
- **Native plan mode**: Main agent uses `EnterPlanMode`/`ExitPlanMode` directly instead of invoking `/task-planner` skill, retaining full context from exploration
- **Claude Code Review CI workflow**: GitHub Actions workflow for automated PR review

### Changed
- **Planning instructions absorbed into `workflow_orchestrator.md`**: No more forked context for planning
- **User gets native plan approval UX** via `ExitPlanMode`

### Fixed
- Removed contradictory Bash instruction in plan mode (agent can't use Bash under delegation)
- Refactored continuation hook to check `tool_name` before accessing `tool_input`
- Anchored regex matcher for PostToolUse hook
- Added `ensure_ascii=False` to `json.dumps` for Unicode preservation

## [1.9.0] - 2026-02-06

### Added
- **Agent Teams dual-mode integration**: Workflows automatically select between isolated subagents and collaborative Agent Teams based on task complexity scoring
- **TeamCreate + Task(team_name) + SendMessage**: Real-time teammate collaboration
- **Automatic mode selection**: `team_mode_score` algorithm (score >= 5 = team mode)
- **Two team patterns**: Simple (multi-perspective exploration) and complex (collaborative implementation)
- **Conditional COMMUNICATION MODE**: All 8 agents support both teammate and subagent behavior
- **Nested teams guard**: Prevents teammates from creating sub-teams

### Fixed
- **Statusline cold start**: Optimized from ~28s to <0.1s (360x improvement) by merging 2 sequential ccusage API calls into 1
- **Non-blocking background cache refresh** for statusline cost data

## [1.8.1] - 2026-01-30

### Added
- **Session cost tracking**: Project-specific cost shown alongside daily total in statusline
- **Claude version display**: Version shown first in statusline row 1
- **Turn duration with sparkline**: Visual trend of last 10 turn times
- **60-second cost caching**: Statusline refresh latency reduced from ~27s to ~1s

### Fixed
- **CWD color**: Changed to cyan for visibility on both light and dark themes

## [1.8.0] - 2026-01-30

### Added
- **breadth-reader skill**: Forked skill for breadth tasks (review many files) with Haiku-powered Explore subagents
- **Implementation task decomposition**: "create X with A, B, C" decomposes into parallel subtasks
- **3-step routing**: Write detection → Breadth task → Route decision
- **Concurrency batching**: `CLAUDE_MAX_CONCURRENT` (default 8) for parallel agent control

### Fixed
- **Context exhaustion in parallel workflows**: Reduced context usage from 70% to ~25%
- **Skip hook for subagents**: PreToolUse hook exits immediately when `CLAUDE_PARENT_SESSION_ID` is set
- **Remove TaskOutput from allowlist**: Each call brought ~20K tokens into context; agents write to files instead
- **Allow Write to temp paths**: Subagents can write to `/tmp/`, `/private/tmp/`, `/var/folders/`
- **Prohibit TaskList polling**: Use completion notifications instead (saves ~15K tokens)
- **SubagentStop race condition**: Removed `clear-delegation-sessions.py` from SubagentStop hooks

## [1.7.0] - 2026-01-26

### Added
- **Tasks API migration**: Migrated from TodoWrite to native Claude Code Tasks API (TaskCreate, TaskUpdate, TaskList, TaskGet)
- **Async hooks**: Added `async: true` for non-blocking hook execution (reminders, cleanup)
- **Structured metadata**: Task metadata uses structured fields (wave, phase_id, agent) instead of encoded strings

### Fixed
- Added stderr flush for async hook output reliability
- Added timeout to stop hook for graceful shutdown

## [1.6.0] - 2026-01-22

### Added
- **Cross-platform Windows compatibility**: All 12 bash hooks converted to Python using `uv run --no-project --script`
- **Windows UTF-8 encoding**: Fixes emoji display issues on Windows terminals
- **Plugin mode workflow continuation**: Stop hook pattern enables automatic workflow continuation after task-planner
- **Cross-platform statusline**: `scripts/statusline.py` with path normalization and workflow state display

### Changed
- **Agent name prefix**: Plugin mode uses `workflow-orchestrator:<agent-name>` format
- **hooks.json renamed to plugin-hooks.json**: Avoids Claude Code 2.1.14+ auto-load conflict
- **install.sh simplified**: Removed unnecessary `chmod +x` step

## [1.5.2] - 2026-01-20

### Changed
- **README media update**: Replaced workflow demo GIF with higher quality version (1000px, 15fps)

## [1.5.1] - 2026-01-20

### Fixed
- **Mandatory decomposition enforcement**: Tasks with enumerable operations (add, subtract, multiply, divide) now MUST decompose into separate subtasks; changed atomicity from example to required rule
- **Redundant planning**: Removed duplicate task-planner invocation from `/delegate` command; `delegate.md` now assumes task-planner already ran in Stage 0

## [1.5.0] - 2026-01-18

### Added
- **Unified task planner architecture**: Consolidated delegation-orchestrator into task-planner for single-stage planning
- **Atomicity validation**: 5-point checklist with tier-based complexity scoring (Tier 1/2/3)
- **Success criteria**: Subtasks can define requirements and verifiable success criterion
- **Ralph-loop execution rules**: Escape rules for dynamic iterative verification

### Changed
- **Architecture simplified**: `delegation-orchestrator` agent removed; functionality merged into task-planner

### Removed
- **`delegation-orchestrator` agent**: Replaced by unified task-planner (agent count reduced from 10 to 8)
- **`/ask` command agents**: Unused agents removed

## [1.4.0] - 2026-01-15

### Added
- **task-planner skill**: Codebase-aware task decomposition skill for planning and breaking down complex tasks into subtasks

## [1.3.0] - 2026-01-11

### Added
- **In-session delegation disable**: `/bypass` command to toggle delegation enforcement on/off without restarting
- **Architecture philosophy documentation**: Comprehensive docs on design principles and patterns

### Fixed
- **ASCII dependency graph format**: Enforced consistent formatting for task dependency visualization

## [1.2.0] - 2026-01-03

### Added
- **Plugin marketplace support**: Plugin system with `plugin.json` and `marketplace.json` for distribution via `claude plugin install workflow-orchestrator@barkain-plugins`

## [1.1.0] - 2026-01-03

### Added
- **Sonnet compliance guardrails**: Guardrails for workflow orchestration to handle model-specific behaviors
- **GitHub Actions CI workflow**: Automated CI pipeline
- **State management system**: DAG visualization and compliance enforcement for task graphs
- **State persistence**: Persistent workflow state across sessions

### Changed
- **Workflow orchestration enhancements**: Improved reliability and state tracking

## [1.0.0] - 2025-11-22

### Added
- **Initial release**: Claude Code delegation system with workflow orchestration
- **Delegation enforcement**: PreToolUse hook blocks non-allowed tools and requires delegation
- **8 specialized agents**: codebase-context-analyzer, code-reviewer, code-cleanup-optimizer, devops-experience-architect, task-completion-verifier, tech-lead-architect, documentation-expert, dependency-manager
- **Workflow orchestrator**: System prompt for task decomposition and parallel execution
- **`/delegate` command**: Plan and execute tasks via workflow orchestrator
- **`/ask` command**: Read-only question answering with forked context
- **install.sh**: Installation script for hooks and agent configurations
