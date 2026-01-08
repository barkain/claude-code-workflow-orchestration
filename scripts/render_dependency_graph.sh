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
#       "content": "[W0:Foundation & Project Setup][root.1.1.1][general-purpose][PARALLEL] Create project structure",
#       "activeForm": "Creating project structure",
#       "status": "in_progress"
#     },
#     ...
#   ]
# }
#
# Metadata encoding in content:
# - [W<n>:<title>] - Wave number and title (required)
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

echo "**DEPENDENCY GRAPH:**"
echo ""

# Build wave data using jq
# Content format: [W<n>:<title>][<phase_id>][<agent>][PARALLEL]? <description>

wave_data=$(echo "$json" | jq -r '
  .todos[] |
  .content |
  # Extract wave number and title: [W0:Title]
  capture("^\\[W(?<wave>[0-9]+):(?<title>[^\\]]+)\\]\\[(?<phase_id>[^\\]]+)\\]\\[(?<agent>[^\\]]+)\\](?<parallel>\\[PARALLEL\\])?\\s*(?<description>.*)$") |
  "\(.wave)|\(.title)|\(.phase_id)|\(.agent)|\(.parallel // "")|\(.description)"
' 2>/dev/null | sort -t'|' -k1,1n)

if [[ -z "$wave_data" ]]; then
    echo "No valid wave data found in TodoWrite JSON" >&2
    exit 1
fi

# Get max wave number
max_wave=$(echo "$wave_data" | cut -d'|' -f1 | sort -n | uniq | tail -1)

# Process each wave
for ((w=0; w<=max_wave; w++)); do
    # Get all phases for this wave
    wave_phases=$(echo "$wave_data" | grep "^${w}|" || true)

    if [[ -z "$wave_phases" ]]; then
        continue
    fi

    # Get wave title from first phase
    wave_title=$(echo "$wave_phases" | head -1 | cut -d'|' -f2)

    # Count phases and check if parallel
    num_phases=$(echo "$wave_phases" | wc -l | tr -d ' ')
    is_parallel=$(echo "$wave_phases" | head -1 | cut -d'|' -f5)

    # Wave header
    if [[ -n "$is_parallel" ]]; then
        echo "Wave $w: $wave_title (parallel)"
    else
        echo "Wave $w: $wave_title"
    fi

    # Render each phase
    line_num=0
    while IFS='|' read -r wave_num title phase_id agent parallel description; do
        line_num=$((line_num + 1))

        # Connector: last uses corner, others use tee
        if [[ $line_num -eq $num_phases ]]; then
            connector="└─"
        else
            connector="├─"
        fi

        # Format with alignment
        printf "%s %-16s  %-30s  [%s]\n" "$connector" "$phase_id" "$description" "$agent"
    done <<< "$wave_phases"

    # Wave separator (except after last wave)
    if [[ $w -lt $max_wave ]]; then
        echo "│"
        echo "▼"
    fi
done
