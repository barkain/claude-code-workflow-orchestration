# Changelog

All notable changes to this project will be documented in this file.

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
