#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
PostToolUse Hook: Task Graph Depth Hint (cross-platform)

Soft enforcement: never blocks. When the active task graph contains atomic
tasks shallower than depth 3, write a hint to stderr. The model can refine
the plan on the next iteration if needed.
"""

import io
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

MIN_DEPTH = 3


def main() -> int:
    """Main entry point. Always returns 0."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    task_graph_file = project_dir / ".claude" / "state" / "active_task_graph.json"

    if not task_graph_file.exists():
        return 0

    try:
        task_graph = json.loads(task_graph_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    violations = []
    execution_plan = task_graph.get("execution_plan", task_graph)
    for wave in execution_plan.get("waves", []):
        for phase in wave.get("phases", []):
            if phase.get("is_atomic") is True and phase.get("depth", 0) < MIN_DEPTH:
                violations.append(
                    f"{phase.get('phase_id', 'unknown')} (depth: {phase.get('depth', 0)})"
                )

    if violations:
        sys.stderr.write(
            f"hint: {len(violations)} atomic task(s) shallower than depth {MIN_DEPTH}: "
            f"{', '.join(violations[:5])}"
            + (f" (+{len(violations) - 5} more)" if len(violations) > 5 else "")
            + ". Deeper decomposition improves parallelization.\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
