#!/usr/bin/env bash
  # ~/.claude/hooks/SubagentStop/remind_todo_update.sh
  # Triggers when a subagent completes execution

  set -euo pipefail

  # Resolve plugin directory (works both in development and when installed)
  PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

  # Get subagent info from environment
  SUBAGENT_TYPE="${SUBAGENT_TYPE:-unknown}"
  SUBAGENT_STATUS="${SUBAGENT_STATUS:-completed}"

  # Only remind on successful completion
  if [[ "$SUBAGENT_STATUS" == "completed" ]]; then
      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "📋 REMINDER: Update TodoWrite task list"
      echo "   Subagent ($SUBAGENT_TYPE) completed successfully"
      echo "   Mark current task as 'completed'"
      echo "   Update next task to 'in_progress' (if multi-step)"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo ""

      # Remind about dependency graph for orchestrator
      if [[ "$SUBAGENT_TYPE" == "delegation-orchestrator" ]] || [[ "$SUBAGENT_TYPE" == *"orchestrat"* ]]; then
          echo "REQUIRED: Render DEPENDENCY GRAPH using box format. Do NOT skip."
          echo ""
      fi
  fi

  exit 0
  