#!/usr/bin/env bash

# Dependency Analysis Algorithm
# Purpose: Analyze task dependencies and build dependency graph
# Based on: Three dependency types from parallel-orchestration-architecture.md
#   1. Parent-child dependencies (implicit from tree structure)
#   2. Data flow dependencies (explicit from context references)
#   3. Ordering dependencies (explicit from sequential connectors)
#
# Usage: ./dependency-analyzer.sh <task_tree_json>
#
# Input JSON format:
# {
#   "tasks": [
#     {"id": "task-1", "parent_id": null, "description": "...", "dependencies": []},
#     {"id": "task-2", "parent_id": "task-1", "description": "...", "dependencies": ["task-1"]}
#   ]
# }
#
# Output JSON format:
# {
#   "dependency_graph": {"task-1": [], "task-2": ["task-1"]},
#   "cycles": [],
#   "valid": true,
#   "error": null
# }

set -euo pipefail

# Parse input (from stdin or file)
INPUT_JSON="${1:-}"

if [[ -z "$INPUT_JSON" ]]; then
    # Read from stdin
    INPUT_JSON=$(cat)
fi

# Temporary files for processing
TEMP_DIR=$(mktemp -d)

# Comprehensive cleanup function handling multiple signals
cleanup() {
    local exit_code=$?

    # Temporarily disable exit on error for cleanup
    set +e

    # Remove temp directory
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR" 2>/dev/null || {
            # If removal fails, log to cleanup registry
            echo "$TEMP_DIR" >> "/tmp/.claude-code-orphaned-temps" 2>/dev/null || true
        }
    fi

    # Remove from active registry
    if [[ -f "/tmp/.claude-code-active-temps" ]]; then
        grep -v "^${TEMP_DIR}$" "/tmp/.claude-code-active-temps" > "/tmp/.claude-code-active-temps.tmp" 2>/dev/null || true
        mv "/tmp/.claude-code-active-temps.tmp" "/tmp/.claude-code-active-temps" 2>/dev/null || true
    fi

    exit $exit_code
}

# Register temp directory for startup cleanup
echo "$TEMP_DIR" >> "/tmp/.claude-code-active-temps"

# Trap multiple signals for comprehensive cleanup
trap cleanup EXIT INT TERM HUP

TASKS_FILE="$TEMP_DIR/tasks.json"
GRAPH_FILE="$TEMP_DIR/graph.json"
CYCLES_FILE="$TEMP_DIR/cycles.json"

# Extract tasks array
echo "$INPUT_JSON" | jq -r '.tasks' > "$TASKS_FILE"

# ============================================================================
# STEP 1: Build dependency graph from task tree
# ============================================================================
build_dependency_graph() {
    local tasks_json=$1
    local output_file=$2

    # Single jq operation - O(n) complexity instead of O(n²)
    # Processes all tasks in one pass without file I/O in loop
    echo "$tasks_json" | jq -r '
    reduce .[] as $task (
        {};
        . + {
            ($task.id): (
                (if $task.parent_id and $task.parent_id != null
                 then [$task.parent_id]
                 else []
                 end) +
                ($task.dependencies // [])
                | unique
            )
        }
    )' > "$output_file"
}

# ============================================================================
# STEP 2: Validate references (check all dependencies exist)
# ============================================================================
validate_references() {
    local graph_file=$1
    local graph=$(cat "$graph_file")

    # Get all task IDs
    local all_task_ids=$(echo "$graph" | jq -r 'keys[]')

    # Check each dependency references a valid task
    local invalid_refs=()
    while read -r task_id; do
        local deps=$(echo "$graph" | jq -r --arg tid "$task_id" '.[$tid][]')
        for dep in $deps; do
            if ! echo "$all_task_ids" | grep -qx "$dep"; then
                invalid_refs+=("Invalid reference: Task $task_id depends on non-existent task $dep")
            fi
        done
    done < <(echo "$all_task_ids")

    if [[ ${#invalid_refs[@]} -gt 0 ]]; then
        echo "false"
        echo "${invalid_refs[@]}" | jq -R -s 'split("\n") | map(select(length > 0))'
        return 0
    fi

    echo "true"
    echo "[]"
    return 0
}

# ============================================================================
# STEP 3: Detect cycles using DFS
# ============================================================================
detect_cycles() {
    local graph_file=$1
    local output_file=$2

    # Use jq to implement cycle detection
    # This is a simplified version - for production, use a proper graph library
    local graph=$(cat "$graph_file")

    # Initialize cycles array
    echo '[]' > "$output_file"

    # Get all task IDs
    local all_task_ids=$(echo "$graph" | jq -r 'keys[]')

    # Perform DFS from each node
    local visited=()
    local rec_stack=()

    detect_cycle_dfs() {
        local node=$1
        local path=("${@:2}")

        # Mark as visited
        visited+=("$node")
        rec_stack+=("$node")
        path+=("$node")

        # Get neighbors
        local neighbors=$(echo "$graph" | jq -r --arg n "$node" '.[$n][]? // empty')

        for neighbor in $neighbors; do
            # Check if neighbor is in recursion stack (cycle detected)
            if [[ ${#rec_stack[@]} -gt 0 ]] && [[ " ${rec_stack[*]} " =~ " $neighbor " ]]; then
                # Found cycle - extract cycle path
                local cycle_start_idx=0
                for i in "${!path[@]}"; do
                    if [[ "${path[$i]}" == "$neighbor" ]]; then
                        cycle_start_idx=$i
                        break
                    fi
                done
                local cycle_path=("${path[@]:$cycle_start_idx}")
                cycle_path+=("$neighbor")

                # Add to cycles file
                local cycle_json=$(printf '%s\n' "${cycle_path[@]}" | jq -R -s 'split("\n") | map(select(length > 0))')
                local current_cycles=$(cat "$output_file")
                echo "$current_cycles" | jq --argjson cycle "$cycle_json" '. + [$cycle]' > "$output_file.tmp"
                mv "$output_file.tmp" "$output_file"
                return 1
            fi

            # Recurse if not visited
            if [[ ${#visited[@]} -eq 0 ]] || [[ ! " ${visited[*]} " =~ " $neighbor " ]]; then
                if ! detect_cycle_dfs "$neighbor" "${path[@]}"; then
                    return 1
                fi
            fi
        done

        # Remove from recursion stack
        local new_rec_stack=()
        if [[ ${#rec_stack[@]} -gt 0 ]]; then
            for item in "${rec_stack[@]}"; do
                [[ "$item" != "$node" ]] && new_rec_stack+=("$item")
            done
        fi
        if [[ ${#new_rec_stack[@]} -gt 0 ]]; then
            rec_stack=("${new_rec_stack[@]}")
        else
            rec_stack=()
        fi

        return 0
    }

    # Run DFS from each unvisited node
    while read -r node; do
        if [[ ${#visited[@]} -eq 0 ]] || [[ ! " ${visited[*]} " =~ " $node " ]]; then
            detect_cycle_dfs "$node" || true
        fi
    done < <(echo "$all_task_ids")

    # Check if any cycles were found
    local cycle_count=$(cat "$output_file" | jq 'length')
    if [[ $cycle_count -gt 0 ]]; then
        return 1
    fi

    return 0
}

# ============================================================================
# Main execution
# ============================================================================

# Build dependency graph
build_dependency_graph "$(cat "$TASKS_FILE")" "$GRAPH_FILE"

# Validate references
VALIDATION_RESULT=$(validate_references "$GRAPH_FILE")
VALID=$(echo "$VALIDATION_RESULT" | head -n1)
INVALID_REFS_JSON=$(echo "$VALIDATION_RESULT" | tail -n +2)

# Detect cycles
if [[ "$VALID" == "true" ]]; then
    if detect_cycles "$GRAPH_FILE" "$CYCLES_FILE"; then
        CYCLES="[]"
        ERROR="null"
    else
        CYCLES=$(cat "$CYCLES_FILE")
        ERROR="\"Circular dependency detected\""
        VALID="false"
    fi
else
    CYCLES="[]"
    # Convert JSON array to a simple string for the error message
    INVALID_REFS_STR=$(echo "$INVALID_REFS_JSON" | jq -r 'join(", ")')
    ERROR=$(echo "$INVALID_REFS_STR" | jq -R -s '.')
fi

# Output result
DEPENDENCY_GRAPH=$(cat "$GRAPH_FILE")
cat <<EOF
{
  "dependency_graph": $DEPENDENCY_GRAPH,
  "cycles": $CYCLES,
  "valid": $VALID,
  "error": $ERROR
}
EOF
