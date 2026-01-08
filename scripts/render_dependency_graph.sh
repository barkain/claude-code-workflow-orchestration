#!/bin/bash
# render_dependency_graph.sh
# Renders a deterministic ASCII dependency graph from JSON execution plan
#
# Usage:
#   ./render_dependency_graph.sh execution_plan.json
#   cat execution_plan.json | ./render_dependency_graph.sh
#
# Output format is fixed - no LLM creativity, always identical for same input

set -e

# Read JSON from file or stdin
if [[ -n "$1" && -f "$1" ]]; then
    json=$(cat "$1")
elif [[ ! -t 0 ]]; then
    json=$(cat)
else
    echo "Usage: $0 <json_file> OR pipe JSON to stdin" >&2
    exit 1
fi

# Validate JSON has waves
if ! echo "$json" | jq -e '.waves' > /dev/null 2>&1; then
    echo "Error: Invalid JSON - missing 'waves' array" >&2
    exit 1
fi

echo "DEPENDENCY GRAPH:"
echo ""

# Get total number of waves
total_waves=$(echo "$json" | jq '.waves | length')

# Process each wave
for ((w=0; w<total_waves; w++)); do
    wave=$(echo "$json" | jq ".waves[$w]")
    wave_id=$(echo "$wave" | jq -r '.wave_id')
    title=$(echo "$wave" | jq -r '.title')
    parallel=$(echo "$wave" | jq -r '.parallel')

    # Wave header
    if [[ "$parallel" == "true" ]]; then
        echo "Wave $wave_id: $title (PARALLEL)"
    else
        echo "Wave $wave_id: $title"
    fi

    # Get phases
    num_phases=$(echo "$wave" | jq '.phases | length')

    for ((p=0; p<num_phases; p++)); do
        phase=$(echo "$wave" | jq ".phases[$p]")
        phase_id=$(echo "$phase" | jq -r '.phase_id')
        description=$(echo "$phase" | jq -r '.description')
        agent=$(echo "$phase" | jq -r '.agent')

        # Determine connector: last/only phase uses corner, others use tee
        if [[ $p -eq $((num_phases - 1)) ]]; then
            connector="└─"
        else
            connector="├─"
        fi

        # Format with alignment (phase_id: 18 chars, description: 33 chars)
        printf "%s %-18s  %-33s  [%s]\n" "$connector" "$phase_id" "$description" "$agent"
    done

    # Wave separator (except after last wave)
    if [[ $w -lt $((total_waves - 1)) ]]; then
        echo "│"
        echo "▼"
    fi
done
