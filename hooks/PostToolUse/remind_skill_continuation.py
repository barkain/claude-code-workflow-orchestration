#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
Remind Claude to continue after ExitPlanMode.

Creates a state file that the Stop hook checks to auto-continue workflow.
Triggers on:
  - PostToolUse for ExitPlanMode tool (plan mode completion)
This is a workaround for plugin mode where additionalContext isn't applied.
"""

import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Setup debug logging (cross-platform temp path)
DEBUG = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
if DEBUG:
    logging.basicConfig(
        filename=str(Path(tempfile.gettempdir()) / "delegation_hook_debug.log"),
        level=logging.DEBUG,
        format="%(asctime)s - remind_skill_continuation - %(message)s",
    )
else:
    logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)

CONTINUATION_CONTEXT = (
    "⚡ IMMEDIATELY PROCEED TO STAGE 1: EXECUTION. "
    "Parse the execution plan and begin delegating phases. DO NOT STOP."
)


def _create_continuation_state(reason: str) -> None:
    """Create state file and emit additionalContext for workflow continuation."""
    state_dir = Path(".claude/state")
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "workflow_continuation_needed.json"
    state_file.write_text(
        json.dumps(
            {
                "reason": reason,
                "action": "continue workflow execution",
            },
            ensure_ascii=False,
        )
    )
    logger.debug("Created state file: %s (reason: %s)", state_file, reason)

    # Also output additionalContext (may work in some contexts)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": CONTINUATION_CONTEXT,
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")


def _zero_violations_counter() -> None:
    """Reset the per-turn delegation violations counter.

    Called when /workflow-orchestrator:delegate runs — the user has chosen the
    right path, so the slate is clean. Subsequent direct tool calls in this
    turn start nudging from zero again.
    """
    state_dir = Path(".claude/state")
    counter_file = state_dir / "delegation_violations.json"
    if not counter_file.exists():
        return
    try:
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        data["violations"] = 0
        data["delegations"] = int(data.get("delegations", 0)) + 1
        counter_file.write_text(json.dumps(data), encoding="utf-8")
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to zero violations counter: %s", e)


def _is_delegate_invocation(data: dict) -> bool:
    """True if this PostToolUse event is /workflow-orchestrator:delegate."""
    tool_input = data.get("tool_input", {}) or {}
    if not isinstance(tool_input, dict):
        return False
    # Skill / SlashCommand carry the command in different fields depending on version
    candidates = [
        str(tool_input.get("command", "")),
        str(tool_input.get("name", "")),
        str(tool_input.get("skill", "")),
        str(tool_input.get("slash_command", "")),
    ]
    return any("delegate" in c.lower() for c in candidates)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        tool_name = data.get("tool_name", "")

        logger.debug("tool_name=%s", tool_name)

        # Case 1: ExitPlanMode tool invoked (plan mode completion)
        if tool_name == "ExitPlanMode":
            logger.debug("ExitPlanMode detected, creating continuation state file")
            _create_continuation_state("plan mode completed")
            return

        # Case 2: /workflow-orchestrator:delegate invoked — zero the nudge counter
        if tool_name in ("Skill", "SlashCommand") and _is_delegate_invocation(data):
            logger.debug("delegate invocation detected, zeroing violations counter")
            _zero_violations_counter()
            return

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug("Error: %s", e)


if __name__ == "__main__":
    main()
