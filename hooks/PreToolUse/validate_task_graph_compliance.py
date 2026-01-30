#!/usr/bin/env python3
"""
PreToolUse Hook: Validate Task Graph Compliance (cross-platform)

Validates that when an active task graph exists, Task invocations
include valid phase IDs that match the current execution wave.

This Python version works on Windows, macOS, and Linux.
"""

import json
import os
import re
import sys
from pathlib import Path

# Maximum stdin size: 1MB (prevents resource exhaustion)
MAX_STDIN_SIZE = 1048576


def main() -> int:
    """Main entry point."""
    # Read stdin with size limit
    try:
        stdin_json = sys.stdin.read(MAX_STDIN_SIZE)
    except Exception:
        stdin_json = ""

    stdin_size = len(stdin_json)

    # Check 1: Detect oversized input
    if stdin_size >= MAX_STDIN_SIZE:
        sys.stderr.write("ERROR: stdin JSON exceeds maximum size (1MB)\n")
        sys.stderr.write(f"Received: {stdin_size} bytes\n")
        return 1

    # Check 2: Detect empty input
    if not stdin_json:
        sys.stderr.write("ERROR: stdin is empty, expected JSON input from PreToolUse hook\n")
        return 1

    # Check 3: Validate JSON syntax
    try:
        tool_input = json.loads(stdin_json)
    except json.JSONDecodeError:
        sys.stderr.write("ERROR: stdin is not valid JSON\n")
        sys.stderr.write(f"Received first 200 chars: {stdin_json[:200]}\n")
        return 1

    # Get tool name from input or first argument
    tool_name = tool_input.get("tool_name", "")
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]

    # Only validate Task tool invocations
    if tool_name != "Task":
        return 0

    # Project directory (supports both project and user scope)
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    task_graph_file = project_dir / ".claude" / "state" / "active_task_graph.json"

    # If no active task graph, allow the Task invocation
    if not task_graph_file.exists():
        return 0

    # Extract the prompt from tool input
    task_prompt = tool_input.get("prompt", "") or tool_input.get("parameters", {}).get("prompt", "")

    if not task_prompt:
        return 0

    # Check if this is a delegation-orchestrator invocation (always allowed)
    subagent_type = tool_input.get("subagent_type", "")
    if subagent_type == "delegation-orchestrator":
        return 0

    # Extract phase ID from the prompt (format: "Phase ID: phase_X_Y")
    phase_match = re.search(r"Phase ID: (phase_\d+_\d+)", task_prompt)
    phase_id = phase_match.group(1) if phase_match else ""

    # Load task graph
    try:
        task_graph = json.loads(task_graph_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"WARNING: Failed to read task graph: {e}\n")
        return 0  # Allow if we can't read the task graph

    # If task graph exists but no phase ID in prompt, this is a compliance violation
    if not phase_id:
        sys.stderr.write("❌ TASK GRAPH COMPLIANCE VIOLATION\n")
        sys.stderr.write("\n")
        sys.stderr.write(f"An active task graph exists at: {task_graph_file}\n")
        sys.stderr.write("But this Task invocation is missing a Phase ID marker.\n")
        sys.stderr.write("\n")
        sys.stderr.write("REQUIRED: Include 'Phase ID: phase_X_Y' at the start of your Task prompt.\n")
        sys.stderr.write("\n")
        sys.stderr.write("Example:\n")
        sys.stderr.write("  Phase ID: phase_0_0\n")
        sys.stderr.write("  Agent: codebase-context-analyzer\n")
        sys.stderr.write("\n")
        sys.stderr.write("  [Your task description...]\n")
        sys.stderr.write("\n")
        sys.stderr.write("If you believe this task graph is outdated, delete it first:\n")
        sys.stderr.write(f"  rm {task_graph_file}\n")
        return 1

    # Validate phase ID exists in task graph
    phase_exists = False
    phase_wave = None
    for wave in task_graph.get("waves", []):
        for phase in wave.get("phases", []):
            if phase.get("phase_id") == phase_id:
                phase_exists = True
                phase_wave = wave.get("wave_id")
                break
        if phase_exists:
            break

    if not phase_exists:
        sys.stderr.write(f"❌ INVALID PHASE ID: {phase_id}\n")
        sys.stderr.write("\n")
        sys.stderr.write("This phase ID does not exist in the active task graph.\n")
        sys.stderr.write("\n")
        sys.stderr.write("Available phases:\n")
        for wave in task_graph.get("waves", []):
            for phase in wave.get("phases", []):
                sys.stderr.write(f"  - {phase.get('phase_id')}\n")
        sys.stderr.write("\n")
        sys.stderr.write("Check your execution plan or clear the task graph:\n")
        sys.stderr.write(f"  rm {task_graph_file}\n")
        return 1

    # Get current wave from task graph
    current_wave = task_graph.get("current_wave", 0)

    # Validate wave order
    if phase_wave is not None and phase_wave > current_wave:
        sys.stderr.write("❌ WAVE ORDER VIOLATION\n")
        sys.stderr.write("\n")
        sys.stderr.write(f"Current wave: {current_wave}\n")
        sys.stderr.write(f"Attempted phase: {phase_id} (wave {phase_wave})\n")
        sys.stderr.write("\n")
        sys.stderr.write(f"Cannot start Wave {phase_wave} tasks while Wave {current_wave} is incomplete.\n")
        sys.stderr.write(f"Complete all Wave {current_wave} phases first.\n")
        return 1

    # Validation passed
    return 0


if __name__ == "__main__":
    sys.exit(main())
