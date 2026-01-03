#!/usr/bin/env bash
# SessionStart Hook: Inject workflow_orchestrator system prompt
#
# This hook runs on session startup/resume/clear/compact and injects the
# workflow_orchestrator.md system prompt into Claude's context. This enables
# automatic multi-step workflow detection, phase decomposition, and intelligent
# delegation orchestration for every session.
#
# Design Decision: Always-on orchestration (no conditional logic)
# - Trust the orchestrator to detect single vs multi-step tasks
# - Simpler implementation, fewer failure modes
# - Consistent behavior across all sessions
#
# Output Format: stdout content is added to Claude's context
# Expected Size: ~27,500 characters (613 lines)
# Timeout: 15-20 seconds recommended in settings.json

set -euo pipefail

# --- PLUGIN ROOT RESOLUTION ---
# Resolve plugin directory (works both in development and when installed)
# CLAUDE_PLUGIN_ROOT is set by Claude Code when running from marketplace
# Fallback navigates from hooks/SessionStart/ up to plugin root
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# --- DEBUG MODE ---
DEBUG_HOOK="${DEBUG_DELEGATION_HOOK:-0}"
DEBUG_FILE="/tmp/delegation_hook_debug.log"

[[ "$DEBUG_HOOK" == "1" ]] && echo "=== SessionStart Hook: $(date) ===" >> "$DEBUG_FILE"
[[ "$DEBUG_HOOK" == "1" ]] && echo "PLUGIN_DIR: $PLUGIN_DIR" >> "$DEBUG_FILE"

# --- Locate workflow_orchestrator.md ---
# Priority order:
# 1. Plugin directory (marketplace or development install)
# 2. Installed location: ~/.claude/system-prompts/workflow_orchestrator.md
# 3. Fallback: Repository src/ location (for development)
# 4. Local .claude directory (project-specific override)

PLUGIN_PATH="${PLUGIN_DIR}/system-prompts/workflow_orchestrator.md"
INSTALLED_PATH="$HOME/.claude/system-prompts/workflow_orchestrator.md"
REPO_PATH="${CLAUDE_PROJECT_DIR:-$PWD}/system-prompts/workflow_orchestrator.md"
LOCAL_CLAUDE_PATH="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/system-prompts/workflow_orchestrator.md"

if [[ -f "$PLUGIN_PATH" ]]; then
  ORCHESTRATOR_FILE="$PLUGIN_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at plugin path: $PLUGIN_PATH" >> "$DEBUG_FILE"
elif [[ -f "$INSTALLED_PATH" ]]; then
  ORCHESTRATOR_FILE="$INSTALLED_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at installed path: $INSTALLED_PATH" >> "$DEBUG_FILE"
elif [[ -f "$REPO_PATH" ]]; then
  ORCHESTRATOR_FILE="$REPO_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at repo path: $REPO_PATH" >> "$DEBUG_FILE"
elif [[ -f "$LOCAL_CLAUDE_PATH" ]]; then
  ORCHESTRATOR_FILE="$LOCAL_CLAUDE_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at local .claude path: $LOCAL_CLAUDE_PATH" >> "$DEBUG_FILE"
else
  # File not found - log error and exit gracefully
  # Don't block session startup, but warn user
  [[ "$DEBUG_HOOK" == "1" ]] && echo "ERROR: workflow_orchestrator.md not found" >> "$DEBUG_FILE"

  echo "⚠️ Warning: workflow_orchestrator.md not found" >&2
  echo "" >&2
  echo "Multi-step workflow orchestration will not be available." >&2
  echo "" >&2
  echo "Expected locations:" >&2
  echo "  - $PLUGIN_PATH (plugin directory)" >&2
  echo "  - $INSTALLED_PATH" >&2
  echo "  - $REPO_PATH" >&2
  echo "  - $LOCAL_CLAUDE_PATH" >&2
  echo "" >&2
  echo "To install: cp -r system-prompts ~/.claude/" >&2

  exit 0  # Exit gracefully - don't block session startup
fi

# --- Inject orchestrator prompt into Claude's context ---
# Output to stdout is automatically added to the session context by Claude Code
# No special formatting needed - just output the file contents

[[ "$DEBUG_HOOK" == "1" ]] && echo "Injecting workflow_orchestrator.md ($(wc -l < "$ORCHESTRATOR_FILE") lines, $(wc -c < "$ORCHESTRATOR_FILE") bytes)" >> "$DEBUG_FILE"

cat "$ORCHESTRATOR_FILE"

[[ "$DEBUG_HOOK" == "1" ]] && echo "SessionStart hook completed successfully" >> "$DEBUG_FILE"

exit 0
