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
        print(f"ERROR: stdin JSON exceeds maximum size (1MB)", file=sys.stderr)
        print(f"Received: {stdin_size} bytes", file=sys.stderr)
        return 1

    # Check 2: Detect empty input
    if not stdin_json:
        print("ERROR: stdin is empty, expected JSON input from PreToolUse hook", file=sys.stderr)
        return 1

    # Check 3: Validate JSON syntax
    try:
        tool_input = json.loads(stdin_json)
    except json.JSONDecodeError:
        print("ERROR: stdin is not valid JSON", file=sys.stderr)
        print(f"Received first 200 chars: {stdin_json[:200]}", file=sys.stderr)
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
        print(f"WARNING: Failed to read task graph: {e}", file=sys.stderr)
        return 0  # Allow if we can't read the task graph

    # If task graph exists but no phase ID in prompt, this is a compliance violation
    if not phase_id:
        print("❌ TASK GRAPH COMPLIANCE VIOLATION", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"An active task graph exists at: {task_graph_file}", file=sys.stderr)
        print("But this Task invocation is missing a Phase ID marker.", file=sys.stderr)
        print("", file=sys.stderr)
        print("REQUIRED: Include 'Phase ID: phase_X_Y' at the start of your Task prompt.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  Phase ID: phase_0_0", file=sys.stderr)
        print("  Agent: codebase-context-analyzer", file=sys.stderr)
        print("", file=sys.stderr)
        print("  [Your task description...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("If you believe this task graph is outdated, delete it first:", file=sys.stderr)
        print(f"  rm {task_graph_file}", file=sys.stderr)
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
        print(f"❌ INVALID PHASE ID: {phase_id}", file=sys.stderr)
        print("", file=sys.stderr)
        print("This phase ID does not exist in the active task graph.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Available phases:", file=sys.stderr)
        for wave in task_graph.get("waves", []):
            for phase in wave.get("phases", []):
                print(f"  - {phase.get('phase_id')}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Check your execution plan or clear the task graph:", file=sys.stderr)
        print(f"  rm {task_graph_file}", file=sys.stderr)
        return 1

    # Get current wave from task graph
    current_wave = task_graph.get("current_wave", 0)

    # Validate wave order
    if phase_wave is not None and phase_wave > current_wave:
        print("❌ WAVE ORDER VIOLATION", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Current wave: {current_wave}", file=sys.stderr)
        print(f"Attempted phase: {phase_id} (wave {phase_wave})", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Cannot start Wave {phase_wave} tasks while Wave {current_wave} is incomplete.", file=sys.stderr)
        print(f"Complete all Wave {current_wave} phases first.", file=sys.stderr)
        return 1

    # Validation passed
    return 0


if __name__ == "__main__":
    sys.exit(main())
