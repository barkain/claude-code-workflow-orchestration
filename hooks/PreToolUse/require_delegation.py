#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
PreToolUse Hook: Delegation Enforcement (cross-platform)

Blocks the 7 work-tool primitives unless a delegation is active.
Subagents and active delegations bypass.

EXIT CODES:
- 0: tool allowed
- 2: tool blocked (work tool without active delegation)
"""

import io
import json
import logging
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger("require_delegation")
logger.setLevel(logging.WARNING)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)

WORK_TOOLS = {
    "Bash",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "MultiEdit",
    "NotebookEdit",
}

BLOCK_MSG = "Run /workflow-orchestrator:delegate <task> first."


def get_state_dir() -> Path:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", str(Path.cwd()))).resolve()
    state_dir = project_dir / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def is_subagent() -> bool:
    return bool(
        os.environ.get("CLAUDE_PARENT_SESSION_ID") or os.environ.get("CLAUDE_AGENT_ID")
    )


def main() -> int:
    if is_subagent():
        return 0

    state_dir = get_state_dir()

    if (state_dir / "delegation_active").exists():
        return 0

    try:
        stdin_data = sys.stdin.read()
        data = json.loads(stdin_data) if stdin_data else {}
    except (OSError, json.JSONDecodeError):
        return 0

    if str(data.get("tool_name", "")) not in WORK_TOOLS:
        return 0

    logger.warning("%s", BLOCK_MSG)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        logger.error("require_delegation hook error: %s", e)
        sys.exit(1)
