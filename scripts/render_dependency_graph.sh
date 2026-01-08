#!/bin/bash
# render_dependency_graph.sh
# Renders ASCII dependency graph from TodoWrite JSON
#
# Usage:
#   ./render_dependency_graph.sh todos.json
#   cat todos.json | ./render_dependency_graph.sh
#
# Input format (TodoWrite JSON):
# {
#   "todos": [
#     {
#       "content": "[W0][root.1.1.1][general-purpose] Create project structure",
#       "activeForm": "Creating project structure",
#       "status": "in_progress"
#     },
#     ...
#   ]
# }
#
# Metadata encoding in content:
# - [W<n>] - Wave number (required)
# - [<phase_id>] - Phase ID (required)
# - [<agent>] - Agent name (required)
# - [PARALLEL] - Optional, indicates parallel wave
# - Rest of string is description

set -e

# Read JSON from file or stdin
if [[ -n "$1" && -f "$1" ]]; then
    json=$(cat "$1")
elif [[ ! -t 0 ]]; then
    json=$(cat)
else
    echo "Usage: $0 <todowrite_json> OR pipe JSON to stdin" >&2
    exit 1
fi

# Validate JSON has todos
if ! echo "$json" | jq -e '.todos' > /dev/null 2>&1; then
    echo "Error: Invalid JSON - missing 'todos' array" >&2
    exit 1
fi

echo "DEPENDENCY GRAPH:"
echo ""

# Use jq to parse and format all data, then process with bash
# Output format: wave_num|phase_id|agent|is_parallel|description
parsed=$(echo "$json" | jq -r '
  .todos[] |
  .content |
  # Extract wave number
  capture("^\\[W(?<wave>[0-9]+)\\]") as $w |
  # Extract phase_id (second bracket)
  capture("\\[W[0-9]+\\]\\[(?<phase>[^\\]]+)\\]") as $p |
  # Extract agent (third bracket)
  capture("\\[W[0-9]+\\]\\[[^\\]]+\\]\\[(?<agent>[^\\]]+)\\]") as $a |
  # Check for PARALLEL
  (if test("\\[PARALLEL\\]") then "1" else "0" end) as $parallel |
  # Extract description (remove all brackets)
  (gsub("\\[[^\\]]*\\]"; "") | gsub("^\\s+|\\s+$"; "")) as $desc |
  "\($w.wave)|\($p.phase)|\($a.agent)|\($parallel)|\($desc)"
' 2>/dev/null || true)

if [[ -z "$parsed" ]]; then
    echo "Error: Could not parse any todos" >&2
    exit 1
fi

# Get max wave number
max_wave=$(echo "$parsed" | cut -d'|' -f1 | sort -n | tail -1)

# Process each wave
for ((w=0; w<=max_wave; w++)); do
    # Get all phases for this wave
    wave_phases=$(echo "$parsed" | grep "^${w}|" || true)

    if [[ -z "$wave_phases" ]]; then
        continue
    fi

    # Count phases and check if parallel
    num_phases=$(echo "$wave_phases" | wc -l | tr -d ' ')
    is_parallel=$(echo "$wave_phases" | head -1 | cut -d'|' -f4)

    # Wave header
    if [[ "$is_parallel" == "1" ]]; then
        echo "Wave $w: (PARALLEL - $num_phases tasks)"
    else
        if [[ "$num_phases" -gt 1 ]]; then
            echo "Wave $w: ($num_phases tasks)"
        else
            echo "Wave $w: (1 task)"
        fi
    fi

    # Render each phase
    line_num=0
    while IFS='|' read -r wave_num phase_id agent parallel description; do
        line_num=$((line_num + 1))

        # Connector: last uses corner, others use tee
        if [[ $line_num -eq $num_phases ]]; then
            connector="└─"
        else
            connector="├─"
        fi

        # Format with alignment
        printf "%s %-18s  %-35s  [%s]\n" "$connector" "$phase_id" "$description" "$agent"
    done <<< "$wave_phases"

    # Wave separator (except after last wave)
    if [[ $w -lt $max_wave ]]; then
        echo "│"
        echo "▼"
    fi
done
