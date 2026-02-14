#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
Remind Claude to continue after task-planner skill or ExitPlanMode.

Creates a state file that the Stop hook checks to auto-continue workflow.
Triggers on:
  - PostToolUse for Skill tool when skill contains "task-planner"
  - PostToolUse for ExitPlanMode tool (plan mode completion)
This is a workaround for plugin mode where additionalContext isn't applied.
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

# Setup debug logging
DEBUG = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
if DEBUG:
    logging.basicConfig(
        filename="/tmp/delegation_hook_debug.log",
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
    state_file.write_text(json.dumps({
        "reason": reason,
        "action": "continue workflow execution",
    }, ensure_ascii=False))
    logger.debug("Created state file: %s (reason: %s)", state_file, reason)

    # Also output additionalContext (may work in some contexts)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": CONTINUATION_CONTEXT,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


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

        # Case 2: task-planner skill invoked (backward compat for skill mode)
        if tool_name == "Skill":
            skill = data.get("tool_input", {}).get("skill", "")
            logger.debug("Skill tool detected, skill=%s", skill)
            if "task-planner" in skill:
                logger.debug("task-planner detected, creating continuation state file")
                _create_continuation_state("task-planner skill completed")
                return

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug("Error: %s", e)


if __name__ == "__main__":
    main()
