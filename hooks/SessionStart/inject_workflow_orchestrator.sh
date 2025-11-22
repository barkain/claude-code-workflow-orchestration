#!/usr/bin/env bash
# SessionStart Hook: Inject WORKFLOW_ORCHESTRATOR system prompt
#
# This hook runs on session startup/resume/clear/compact and injects the
# WORKFLOW_ORCHESTRATOR.md system prompt into Claude's context. This enables
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

# --- DEBUG MODE ---
DEBUG_HOOK="${DEBUG_DELEGATION_HOOK:-0}"
DEBUG_FILE="/tmp/delegation_hook_debug.log"

[[ "$DEBUG_HOOK" == "1" ]] && echo "=== SessionStart Hook: $(date) ===" >> "$DEBUG_FILE"

# --- Locate WORKFLOW_ORCHESTRATOR.md ---
# Priority order:
# 1. Installed location: ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md
# 2. Fallback: Repository location (for development)

INSTALLED_PATH="$HOME/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md"
REPO_PATH="${CLAUDE_PROJECT_DIR:-$PWD}/system-prompts/WORKFLOW_ORCHESTRATOR.md"

if [[ -f "$INSTALLED_PATH" ]]; then
  ORCHESTRATOR_FILE="$INSTALLED_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at installed path: $INSTALLED_PATH" >> "$DEBUG_FILE"
elif [[ -f "$REPO_PATH" ]]; then
  ORCHESTRATOR_FILE="$REPO_PATH"
  [[ "$DEBUG_HOOK" == "1" ]] && echo "Found orchestrator at repo path: $REPO_PATH" >> "$DEBUG_FILE"
else
  # File not found - log error and exit gracefully
  # Don't block session startup, but warn user
  [[ "$DEBUG_HOOK" == "1" ]] && echo "ERROR: WORKFLOW_ORCHESTRATOR.md not found" >> "$DEBUG_FILE"

  echo "⚠️ Warning: WORKFLOW_ORCHESTRATOR.md not found" >&2
  echo "" >&2
  echo "Multi-step workflow orchestration will not be available." >&2
  echo "" >&2
  echo "Expected locations:" >&2
  echo "  - $INSTALLED_PATH" >&2
  echo "  - $REPO_PATH" >&2
  echo "" >&2
  echo "To install: cp -r system-prompts ~/.claude/" >&2

  exit 0  # Exit gracefully - don't block session startup
fi

# --- Inject orchestrator prompt into Claude's context ---
# Output to stdout is automatically added to the session context by Claude Code
# No special formatting needed - just output the file contents

[[ "$DEBUG_HOOK" == "1" ]] && echo "Injecting WORKFLOW_ORCHESTRATOR.md ($(wc -l < "$ORCHESTRATOR_FILE") lines, $(wc -c < "$ORCHESTRATOR_FILE") bytes)" >> "$DEBUG_FILE"

cat "$ORCHESTRATOR_FILE"

[[ "$DEBUG_HOOK" == "1" ]] && echo "SessionStart hook completed successfully" >> "$DEBUG_FILE"

exit 0
