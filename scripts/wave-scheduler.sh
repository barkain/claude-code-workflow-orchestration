#!/usr/bin/env bash

# Wave Scheduling Algorithm
# Purpose: Assign tasks to execution waves based on dependency graph
# Based on: Topological sort with wave assignment from parallel-orchestration-architecture.md
#
# Algorithm:
#   1. Topologically sort tasks by dependencies
#   2. Group tasks into waves (tasks with no outstanding dependencies in same wave)
#   3. Apply parallelism limit (max 3 tasks per sub-wave)
#
# Usage: ./wave-scheduler.sh <dependency_graph_json> [max_parallel]
#
# Input JSON format:
# {
#   "dependency_graph": {"task-1": [], "task-2": ["task-1"], "task-3": ["task-1"]},
#   "atomic_tasks": ["task-1", "task-2", "task-3"]
# }
#
# Output JSON format:
# {
#   "wave_assignments": {"task-1": 0, "task-2": 1, "task-3": 1},
#   "total_waves": 2,
#   "parallel_opportunities": 2,
#   "execution_plan": [
#     {"wave": 0, "tasks": ["task-1"], "sub_waves": [[["task-1"]]]},
#     {"wave": 1, "tasks": ["task-2", "task-3"], "sub_waves": [[["task-2", "task-3"]]]}
#   ]
# }

set -euo pipefail

# Configuration
MAX_PARALLEL_DEFAULT=3
MAX_PARALLEL="${2:-$MAX_PARALLEL_DEFAULT}"

# Parse input
INPUT_JSON="${1:-}"

if [[ -z "$INPUT_JSON" ]]; then
    INPUT_JSON=$(cat)
elif [[ "$INPUT_JSON" == "/dev/stdin" ]] || [[ "$INPUT_JSON" == "-" ]]; then
    INPUT_JSON=$(cat)
elif [[ -f "$INPUT_JSON" ]]; then
    INPUT_JSON=$(cat "$INPUT_JSON")
fi

# Temporary files
TEMP_DIR=$(mktemp -d)

# Comprehensive cleanup function handling multiple signals
cleanup() {
    local exit_code=$?

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

GRAPH_FILE="$TEMP_DIR/graph.json"
ATOMIC_TASKS_FILE="$TEMP_DIR/atomic_tasks.json"
WAVES_FILE="$TEMP_DIR/waves.json"

# Extract dependency graph and atomic tasks
echo "$INPUT_JSON" | jq -r '.dependency_graph' > "$GRAPH_FILE"
echo "$INPUT_JSON" | jq -r '.atomic_tasks // []' > "$ATOMIC_TASKS_FILE"

# ============================================================================
# STEP 1: Filter to atomic tasks only (only these are executable)
# ============================================================================
filter_to_atomic_tasks() {
    local graph_file=$1
    local atomic_tasks_file=$2
    local output_file=$3

    local graph=$(cat "$graph_file")
    local atomic_tasks=$(cat "$atomic_tasks_file")

    # If no atomic tasks specified, use all tasks
    if [[ $(echo "$atomic_tasks" | jq 'length') -eq 0 ]]; then
        cp "$graph_file" "$output_file"
        return
    fi

    # Filter graph to only include atomic tasks
    echo '{}' > "$output_file"
    echo "$atomic_tasks" | jq -r '.[]' | while read -r task_id; do
        local deps=$(echo "$graph" | jq --arg tid "$task_id" '.[$tid] // []')
        local current=$(cat "$output_file")
        echo "$current" | jq --arg tid "$task_id" --argjson deps "$deps" \
            '.[$tid] = $deps' > "$output_file.tmp"
        mv "$output_file.tmp" "$output_file"
    done
}

# ============================================================================
# STEP 2: Assign waves using topological sort
# ============================================================================
assign_waves() {
    local graph_file=$1
    local output_file=$2

    local graph=$(cat "$graph_file")

    # Initialize wave assignments
    echo '{}' > "$output_file"

    # Get all task IDs
    local all_tasks=$(echo "$graph" | jq -r 'keys[]')
    local unscheduled=($all_tasks)
    local scheduled=()
    local current_wave=0

    # Continue until all tasks are scheduled
    while [[ ${#unscheduled[@]} -gt 0 ]]; do
        local ready_tasks=()

        # Find tasks ready for current wave (all dependencies satisfied)
        for task_id in "${unscheduled[@]}"; do
            local deps=$(echo "$graph" | jq -r --arg tid "$task_id" '.[$tid][]? // empty')
            local all_deps_met=true

            for dep in $deps; do
                if [[ ${#scheduled[@]} -eq 0 ]] || [[ ! " ${scheduled[*]} " =~ " $dep " ]]; then
                    all_deps_met=false
                    break
                fi
            done

            if [[ "$all_deps_met" == "true" ]]; then
                ready_tasks+=("$task_id")
            fi
        done

        # Check for deadlock (no tasks ready but tasks remain)
        if [[ ${#ready_tasks[@]} -eq 0 ]]; then
            echo "Error: No tasks ready for scheduling (possible cycle)" >&2
            local remaining=$(printf '%s\n' "${unscheduled[@]}" | jq -R -s 'split("\n") | map(select(length > 0))')
            cat <<EOF
{
  "wave_assignments": {},
  "total_waves": 0,
  "parallel_opportunities": 0,
  "execution_plan": [],
  "error": "Scheduling deadlock detected",
  "remaining_tasks": $remaining
}
EOF
            exit 1
        fi

        # Assign ready tasks to current wave
        for task_id in "${ready_tasks[@]}"; do
            local current_assignments=$(cat "$output_file")
            echo "$current_assignments" | jq --arg tid "$task_id" --argjson wave "$current_wave" \
                '.[$tid] = $wave' > "$output_file.tmp"
            mv "$output_file.tmp" "$output_file"

            scheduled+=("$task_id")
        done

        # Remove scheduled tasks from unscheduled
        local new_unscheduled=()
        for task in "${unscheduled[@]}"; do
            if [[ ${#ready_tasks[@]} -eq 0 ]] || [[ ! " ${ready_tasks[*]} " =~ " $task " ]]; then
                new_unscheduled+=("$task")
            fi
        done
        if [[ ${#new_unscheduled[@]} -gt 0 ]]; then
            unscheduled=("${new_unscheduled[@]}")
        else
            unscheduled=()
        fi

        ((current_wave++)) || true
    done

    echo "$current_wave" > "$TEMP_DIR/total_waves"
}

# ============================================================================
# STEP 3: Build execution plan with sub-waves (apply parallelism limit)
# ============================================================================
build_execution_plan() {
    local wave_assignments_file=$1
    local total_waves=$2
    local max_parallel=$3
    local output_file=$4

    local wave_assignments=$(cat "$wave_assignments_file")

    echo '[]' > "$output_file"

    # Group tasks by wave
    for ((wave=0; wave<total_waves; wave++)); do
        local wave_tasks=$(echo "$wave_assignments" | jq -r \
            --arg w "$wave" 'to_entries | map(select(.value == ($w | tonumber)) | .key) | .[]')

        # Convert to array
        local tasks_array=($wave_tasks)

        # Split into sub-waves based on parallelism limit
        local sub_waves='[]'
        local i=0
        while [[ $i -lt ${#tasks_array[@]} ]]; do
            local sub_wave='[]'
            local count=0
            while [[ $count -lt $max_parallel && $i -lt ${#tasks_array[@]} ]]; do
                local task="${tasks_array[$i]}"
                sub_wave=$(echo "$sub_wave" | jq --arg t "$task" '. + [$t]')
                ((i++)) || true
                ((count++)) || true
            done
            sub_waves=$(echo "$sub_waves" | jq --argjson sw "$sub_wave" '. + [$sw]')
        done

        # Create wave entry
        local wave_tasks_json=$(printf '%s\n' "${tasks_array[@]}" | jq -R -s 'split("\n") | map(select(length > 0))')
        local wave_entry=$(cat <<EOF
{
  "wave": $wave,
  "tasks": $wave_tasks_json,
  "sub_waves": [$sub_waves]
}
EOF
)

        local current_plan=$(cat "$output_file")
        echo "$current_plan" | jq --argjson entry "$wave_entry" '. + [$entry]' > "$output_file.tmp"
        mv "$output_file.tmp" "$output_file"
    done
}

# ============================================================================
# STEP 4: Calculate parallel opportunities
# ============================================================================
calculate_parallel_opportunities() {
    local wave_assignments_file=$1
    local total_waves=$2

    local wave_assignments=$(cat "$wave_assignments_file")
    local opportunities=0

    # Count waves with more than 1 task
    for ((wave=0; wave<total_waves; wave++)); do
        local task_count=$(echo "$wave_assignments" | jq -r \
            --arg w "$wave" '[to_entries | map(select(.value == ($w | tonumber)))] | length')

        if [[ $task_count -gt 1 ]]; then
            ((opportunities += task_count - 1)) || true
        fi
    done

    echo "$opportunities"
}

# ============================================================================
# Main execution
# ============================================================================

# Filter to atomic tasks
FILTERED_GRAPH="$TEMP_DIR/filtered_graph.json"
filter_to_atomic_tasks "$GRAPH_FILE" "$ATOMIC_TASKS_FILE" "$FILTERED_GRAPH"

# Assign waves
assign_waves "$FILTERED_GRAPH" "$WAVES_FILE"
TOTAL_WAVES=$(cat "$TEMP_DIR/total_waves")

# Build execution plan
EXECUTION_PLAN_FILE="$TEMP_DIR/execution_plan.json"
build_execution_plan "$WAVES_FILE" "$TOTAL_WAVES" "$MAX_PARALLEL" "$EXECUTION_PLAN_FILE"

# Calculate parallel opportunities
PARALLEL_OPPORTUNITIES=$(calculate_parallel_opportunities "$WAVES_FILE" "$TOTAL_WAVES")

# Output final result
WAVE_ASSIGNMENTS=$(cat "$WAVES_FILE")
EXECUTION_PLAN=$(cat "$EXECUTION_PLAN_FILE")

cat <<EOF
{
  "wave_assignments": $WAVE_ASSIGNMENTS,
  "total_waves": $TOTAL_WAVES,
  "parallel_opportunities": $PARALLEL_OPPORTUNITIES,
  "execution_plan": $EXECUTION_PLAN,
  "error": null
}
EOF
