#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
PreToolUse Hook: Task Graph Compliance Hint (cross-platform)

Soft enforcement: never blocks. When an active task graph exists and an
Agent/Task spawn doesn't match the current wave, write a hint to stderr.
The model can self-correct on the next call. Wave/dependency violations no
longer halt execution.
"""

import json
import os
import re
import sys
from pathlib import Path

MAX_STDIN_SIZE = 1048576


def main() -> int:
    """Main entry point. Always returns 0."""
    state_dir = (
        Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())) / ".claude" / "state"
    )

    # Team mode handles its own dependency tracking
    if (state_dir / "team_mode_active").exists():
        return 0

    try:
        stdin_json = sys.stdin.read(MAX_STDIN_SIZE)
        tool_input = json.loads(stdin_json) if stdin_json else {}
    except (OSError, json.JSONDecodeError):
        return 0

    tool_name = tool_input.get("tool_name", "")
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]

    if tool_name not in ("Agent", "Task", "SubagentTask", "AgentTask"):
        return 0

    task_graph_file = state_dir / "active_task_graph.json"
    if not task_graph_file.exists():
        return 0

    task_prompt = tool_input.get("prompt", "") or tool_input.get("parameters", {}).get(
        "prompt", ""
    )
    if not task_prompt:
        return 0

    if tool_input.get("subagent_type", "") == "delegation-orchestrator":
        return 0

    try:
        task_graph = json.loads(task_graph_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    phase_match = re.search(r"Phase ID: (phase_\d+_\d+)", task_prompt)
    phase_id = phase_match.group(1) if phase_match else ""

    if not phase_id:
        sys.stderr.write(
            "hint: Agent/Task spawn missing 'Phase ID: phase_X_Y' marker "
            "(active task graph at .claude/state/active_task_graph.json).\n"
        )
        return 0

    phase_wave = None
    for wave in task_graph.get("waves", []):
        for phase in wave.get("phases", []):
            if phase.get("phase_id") == phase_id:
                phase_wave = wave.get("wave_id")
                break
        if phase_wave is not None:
            break

    if phase_wave is None:
        sys.stderr.write(
            f"hint: phase ID '{phase_id}' not found in active task graph.\n"
        )
        return 0

    current_wave = task_graph.get("current_wave", 0)
    if phase_wave > current_wave:
        sys.stderr.write(
            f"hint: spawning {phase_id} (wave {phase_wave}) while wave "
            f"{current_wave} is incomplete — out-of-order execution.\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
