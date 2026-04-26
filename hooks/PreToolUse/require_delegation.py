#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
PreToolUse Hook: Adaptive Delegation Nudge (cross-platform)

Soft enforcement: never blocks. Tracks per-turn direct work-tool calls from
the main agent and writes an escalating reminder to stderr. Cost (and signal)
scales with violation count — silent for compliant sessions, louder when the
main agent is repeatedly bypassing /workflow-orchestrator:delegate.

Violation set is small and stable: only the 7 work-doing primitives that
existed before the plugin and won't be renamed. New Claude Code tools never
trigger nudges.

Counter is reset by UserPromptSubmit (new turn) and zeroed when
/workflow-orchestrator:delegate runs (handled by remind_skill_continuation.py).

EXIT CODES:
- 0: always (this hook never blocks)
"""

import io
import json
import logging
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger("require_delegation")
logger.setLevel(logging.WARNING)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)

# Stable, work-doing primitives. New Claude Code tools never appear here.
WORK_TOOLS = {
    "Bash",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "MultiEdit",
    "NotebookEdit",
}


def get_state_dir() -> Path:
    """Get the state directory path."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", str(Path.cwd()))).resolve()
    state_dir = project_dir / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def is_subagent() -> bool:
    """True if running inside a subagent (delegation in progress)."""
    return bool(
        os.environ.get("CLAUDE_PARENT_SESSION_ID") or os.environ.get("CLAUDE_AGENT_ID")
    )


def load_violations(path: Path) -> dict[str, int | str]:
    """Load violations counter, or return a fresh one."""
    if not path.exists():
        return {"violations": 0, "delegations": 0, "turn_id": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"violations": 0, "delegations": 0, "turn_id": ""}


def save_violations(path: Path, data: dict[str, int | str]) -> None:
    """Persist violations counter."""
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def message_for(count: int) -> str | None:
    """Pick the escalation message for a given violation count.

    Token cost scales with severity. Compliant sessions pay 0 tokens.
    """
    if count <= 0:
        return None
    if count == 1:
        return (
            "STOP. This tool call bypasses delegation. Abandon this step "
            "and run: /workflow-orchestrator:delegate <your task>"
        )
    if count == 2:
        return (
            "STOP. 2nd direct tool call this turn. The main agent does not "
            "execute work tools. Run: /workflow-orchestrator:delegate <your task>"
        )
    return (
        f"STOP. {count} direct tool calls bypassing delegation. You are "
        "losing planning, parallelization, and context isolation. Abandon "
        "the current plan and run: /workflow-orchestrator:delegate <your task>"
    )


def main() -> int:
    """Main entry point. Always returns 0."""
    # Subagents are executing a delegation — never count their tool use.
    if is_subagent():
        return 0

    state_dir = get_state_dir()

    # If a delegation is active in this session, the main agent is steering
    # subagents — direct tool use is fine.
    if (state_dir / "delegation_active").exists():
        return 0

    # Read tool name from stdin
    try:
        stdin_data = sys.stdin.read()
        data = json.loads(stdin_data) if stdin_data else {}
    except (OSError, json.JSONDecodeError):
        return 0

    tool_name = str(data.get("tool_name", ""))
    if tool_name not in WORK_TOOLS:
        return 0

    # Count + nudge
    counter_file = state_dir / "delegation_violations.json"
    state = load_violations(counter_file)
    count = int(state.get("violations", 0)) + 1
    state["violations"] = count
    save_violations(counter_file, state)

    msg = message_for(count)
    if msg:
        logger.warning("%s", msg)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        # Surface internal errors per hook exit-code policy (1 = hook error).
        # Exit 1 is a non-blocking error in Claude Code — the tool call still
        # proceeds, but the failure is visible in debug output.
        logger.error("require_delegation hook error: %s", e)
        sys.exit(1)
