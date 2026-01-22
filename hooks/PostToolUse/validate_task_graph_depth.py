#!/usr/bin/env python3
"""
PostToolUse Hook: Validate Task Graph Depth Enforcement (cross-platform)

PURPOSE: Enforce minimum depth-3 decomposition for all atomic tasks

TRIGGER: After Task tool invocations

VALIDATION:
- Reads from .claude/state/active_task_graph.json
- Finds all tasks with is_atomic: true
- BLOCKS execution (exit 1) if any atomic task has depth < 3
- Outputs clear error message showing violations

This Python version works on Windows, macOS, and Linux.
"""

import io
import json
import os
import sys

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

# Configuration
MIN_DEPTH = 3


def main() -> int:
    """Main entry point."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    task_graph_file = project_dir / ".claude" / "state" / "active_task_graph.json"

    # Check if task graph file exists
    if not task_graph_file.exists():
        # No task graph file - skip validation (this is normal for non-workflow tasks)
        return 0

    # Load task graph
    try:
        task_graph = json.loads(task_graph_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Failed to read task graph: {e}", file=sys.stderr)
        return 1

    # Extract all phases from all waves
    # Find phases with is_atomic: true and depth < 3
    violations = []

    execution_plan = task_graph.get("execution_plan", task_graph)
    for wave in execution_plan.get("waves", []):
        for phase in wave.get("phases", []):
            if phase.get("is_atomic") is True and phase.get("depth", 0) < MIN_DEPTH:
                phase_id = phase.get("phase_id", "unknown")
                depth = phase.get("depth", 0)
                violations.append(f"{phase_id} (depth: {depth})")

    # Check for violations
    if violations:
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
        print("❌ TASK GRAPH VALIDATION FAILED: Depth-3 Enforcement", file=sys.stderr)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
        print("", file=sys.stderr)
        print("The following atomic tasks violate the minimum depth-3 constraint:", file=sys.stderr)
        print("", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"REQUIREMENT: All atomic tasks MUST have depth >= {MIN_DEPTH}", file=sys.stderr)
        print("", file=sys.stderr)
        print("WHY THIS MATTERS:", file=sys.stderr)
        print("- Shallow decomposition leads to coarse-grained tasks", file=sys.stderr)
        print("- Reduces parallelization opportunities", file=sys.stderr)
        print("- Makes dependency tracking less precise", file=sys.stderr)
        print("- Violates system design constraints", file=sys.stderr)
        print("", file=sys.stderr)
        print("ACTION REQUIRED:", file=sys.stderr)
        print("1. Return to delegation-orchestrator", file=sys.stderr)
        print("2. Decompose flagged tasks further", file=sys.stderr)
        print(f"3. Ensure all leaf nodes have depth >= {MIN_DEPTH}", file=sys.stderr)
        print("4. Re-generate task graph with proper decomposition", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"LOCATION: {task_graph_file}", file=sys.stderr)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
        return 1

    # All atomic tasks have depth >= 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
