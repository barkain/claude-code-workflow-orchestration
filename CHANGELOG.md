# Changelog

All notable changes to this project will be documented in this file.

## [1.15.1] - 2026-04-04

### Fixed
- **Worktree directory/branch detection**: Statusline now uses `cwd` from Claude Code's stdin JSON instead of `os.getcwd()`, correctly reflecting the working directory when Claude switches to a git worktree

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
- Token-efficient CLI usage: behavioral guidance injection and output compression hook for reduced context consumption
- Mandatory multi-agent execution: all plans now produce 2+ subtasks
- Token efficiency rules enforced across all 8 agent definitions
- `inject_token_efficiency.py` SessionStart hook and `token_rewrite_hook.py` PreToolUse hook

### Changed
- Reorganized statusline layout: static info on row 1, metrics on row 2
- Removed `alwaysThinkingEnabled` from settings

## [1.11.1] - 2026-03-10

### Fixed
- Added `ToolSearch` to delegation policy allowlist to prevent deadlock when fetching deferred tool schemas
- Fixed delegation error message to use correct skill name (`/workflow-orchestrator:delegate` instead of `/delegate`)
- Disabled delegation hook in CI review workflow to allow Claude Code review action to function
- Updated documentation allowlists in CLAUDE.md, ARCHITECTURE_QUICK_REFERENCE.md, hook-debugging.md, and ARCHITECTURE_PHILOSOPHY.md to include ToolSearch

## [1.11.0] - 2026-03-09

### Added
- Initial release with workflow orchestration framework
