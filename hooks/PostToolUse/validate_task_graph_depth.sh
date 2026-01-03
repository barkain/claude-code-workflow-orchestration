#!/usr/bin/env bash
#
# PostToolUse Hook: Validate Task Graph Depth Enforcement
#
# PURPOSE: Enforce minimum depth-3 decomposition for all atomic tasks
#
# TRIGGER: After Task tool invocations
#
# VALIDATION:
# - Reads from .claude/state/active_task_graph.json
# - Finds all tasks with is_atomic: true
# - BLOCKS execution (exit 1) if any atomic task has depth < 3
# - Outputs clear error message showing violations
#
# EXIT CODES:
# - 0: All atomic tasks have depth >= 3 (validation passed)
# - 0: Task graph file doesn't exist (skip validation)
# - 1: Validation failed (atomic tasks with depth < 3 found)
#

set -euo pipefail

# Configuration
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
TASK_GRAPH_FILE="$PROJECT_DIR/.claude/state/active_task_graph.json"
MIN_DEPTH=3

# Check if task graph file exists
if [[ ! -f "$TASK_GRAPH_FILE" ]]; then
    # No task graph file - skip validation (this is normal for non-workflow tasks)
    exit 0
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required for task graph validation but not found" >&2
    exit 1
fi

# Extract all phases from all waves
# Find phases with is_atomic: true and depth < 3
violations=$(jq -r '
  .waves[]?
  | .phases[]?
  | select(.is_atomic == true and .depth < 3)
  | "\(.phase_id) (depth: \(.depth))"
' "$TASK_GRAPH_FILE" 2>/dev/null)

# Check for violations
if [[ -n "$violations" ]]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "❌ TASK GRAPH VALIDATION FAILED: Depth-3 Enforcement" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2
    echo "The following atomic tasks violate the minimum depth-3 constraint:" >&2
    echo "" >&2
    echo "$violations" >&2
    echo "" >&2
    echo "REQUIREMENT: All atomic tasks MUST have depth >= $MIN_DEPTH" >&2
    echo "" >&2
    echo "WHY THIS MATTERS:" >&2
    echo "- Shallow decomposition leads to coarse-grained tasks" >&2
    echo "- Reduces parallelization opportunities" >&2
    echo "- Makes dependency tracking less precise" >&2
    echo "- Violates system design constraints" >&2
    echo "" >&2
    echo "ACTION REQUIRED:" >&2
    echo "1. Return to delegation-orchestrator" >&2
    echo "2. Decompose flagged tasks further" >&2
    echo "3. Ensure all leaf nodes have depth >= $MIN_DEPTH" >&2
    echo "4. Re-generate task graph with proper decomposition" >&2
    echo "" >&2
    echo "LOCATION: $TASK_GRAPH_FILE" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    exit 1
fi

# All atomic tasks have depth >= 3
exit 0
