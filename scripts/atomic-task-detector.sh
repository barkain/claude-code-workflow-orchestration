#!/usr/bin/env bash

# Atomic Task Detection Algorithm
# Purpose: Determine if a task should be treated as atomic (indivisible)
# Based on: 7-step heuristic algorithm from parallel-orchestration-architecture.md
#
# Usage: ./atomic-task-detector.sh "<task_description>" <current_depth> [max_depth]
#
# Returns: JSON with format {"is_atomic": true/false, "reason": "...", "confidence": 0.0-1.0}

set -euo pipefail

# Signal handling for graceful cleanup
cleanup() {
    local exit_code=$?
    # No temp files to clean, but handler ensures proper exit codes
    exit $exit_code
}

# Trap multiple signals for comprehensive cleanup
trap cleanup EXIT INT TERM HUP

# Configuration
MAX_DEPTH_DEFAULT=3
CONFIDENCE_HIGH=0.95
CONFIDENCE_MEDIUM=0.75
CONFIDENCE_LOW=0.50

# Parse arguments
TASK_DESCRIPTION="${1:-}"
CURRENT_DEPTH="${2:-0}"
MAX_DEPTH="${3:-$MAX_DEPTH_DEFAULT}"

if [[ -z "$TASK_DESCRIPTION" ]]; then
    echo '{"is_atomic": false, "reason": "Empty task description", "confidence": 0.0}' >&2
    exit 1
fi

# Convert to lowercase for pattern matching
TASK_LOWER=$(echo "$TASK_DESCRIPTION" | tr '[:upper:]' '[:lower:]')

# Helper function to return JSON result
return_result() {
    local is_atomic=$1
    local reason=$2
    local confidence=$3
    echo "{\"is_atomic\": $is_atomic, \"reason\": \"$reason\", \"confidence\": $confidence}"
    exit 0
}

# ============================================================================
# STEP 1: Enforce minimum 3-level decomposition depth
# ============================================================================
# Tasks MUST be decomposed to at least depth 3 before atomic validation
MIN_DEPTH=3
if [[ $CURRENT_DEPTH -lt $MIN_DEPTH ]]; then
    return_result false "Below minimum decomposition depth ($CURRENT_DEPTH < $MIN_DEPTH)" $CONFIDENCE_HIGH
fi

# ============================================================================
# STEP 2: Check depth limit (safety valve)
# ============================================================================
if [[ $CURRENT_DEPTH -ge $MAX_DEPTH ]]; then
    return_result true "Reached maximum depth ($MAX_DEPTH)" $CONFIDENCE_HIGH
fi

# ============================================================================
# STEP 3: Check explicit atomic markers
# ============================================================================
if echo "$TASK_LOWER" | grep -qE '\(atomic\)|\(single task\)|\(do not decompose\)'; then
    return_result true "Explicit atomic marker found" $CONFIDENCE_HIGH
fi

# ============================================================================
# STEP 4: Check single tool operation patterns
# ============================================================================
# File operations
if echo "$TASK_LOWER" | grep -qE '^(read|write|edit|delete|rm|mv|cp)\s+[a-zA-Z0-9/_.-]+$'; then
    return_result true "Single file operation detected" $CONFIDENCE_HIGH
fi

# Single command execution
if echo "$TASK_LOWER" | grep -qE '^run\s+[a-zA-Z0-9_. -]+$'; then
    return_result true "Single command execution detected" $CONFIDENCE_HIGH
fi

# Search operations
if echo "$TASK_LOWER" | grep -qE '^(grep|find|glob|search)\s+'; then
    return_result true "Single search operation detected" $CONFIDENCE_HIGH
fi

# ============================================================================
# STEP 5: Check for conjunctions and sequential connectors
# ============================================================================
if echo "$TASK_LOWER" | grep -qE '\band\b|\bthen\b|\balso\b|\badditionally\b|\bafter\b|\bnext\b|\bfollowed by\b'; then
    return_result false "Contains conjunctions/sequential connectors" $CONFIDENCE_MEDIUM
fi

# ============================================================================
# STEP 6: Count action verbs
# ============================================================================
# Common action verbs in software tasks
# Single grep with all verbs - replaces 25+ separate grep processes
VERB_COUNT=$(echo "$TASK_LOWER" | grep -owE 'read|write|edit|delete|create|remove|update|modify|implement|refactor|debug|test|deploy|analyze|fix|validate|configure|setup|install|run|execute|build|compile|lint|format|document' | wc -l | tr -d ' ')

if [[ $VERB_COUNT -le 1 ]]; then
    return_result true "Single verb detected (count: $VERB_COUNT)" $CONFIDENCE_MEDIUM
fi

# ============================================================================
# STEP 7: Check for narrow scope indicators
# ============================================================================
if echo "$TASK_LOWER" | grep -qE '\bfunction\b|\bclass\b|\bmethod\b|\bfile\b|\bline\s+[0-9]+|\bmodule\b|\bsingle\b'; then
    return_result true "Narrow scope detected" $CONFIDENCE_MEDIUM
fi

# ============================================================================
# STEP 8: Default - task appears decomposable
# ============================================================================
# If task has multiple verbs and no narrow scope, likely decomposable
if [[ $VERB_COUNT -gt 2 ]]; then
    return_result false "Multiple verbs detected (count: $VERB_COUNT), task appears decomposable" $CONFIDENCE_LOW
else
    return_result false "Task appears decomposable" $CONFIDENCE_LOW
fi
