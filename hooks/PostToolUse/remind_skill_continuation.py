#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
Remind Claude to continue after task-planner skill.

Creates a state file that the Stop hook checks to auto-continue workflow.
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


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        skill = data.get("tool_input", {}).get("skill", "")

        logger.debug(f"Skill: {skill}")

        # Check if task-planner skill was invoked
        if "task-planner" in skill:
            # Always create state file when task-planner is invoked
            # The tool_result is empty for Skill tools in PostToolUse hooks
            # so we can't check for "Ready" status here
            logger.debug("task-planner detected, creating continuation state file")

            # Create state file to signal Stop hook to auto-continue
            state_dir = Path(".claude/state")
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / "workflow_continuation_needed.json"
            state_file.write_text(json.dumps({
                "reason": "task-planner skill completed",
                "action": "continue workflow execution"
            }))
            logger.debug(f"Created state file: {state_file}")

            # Also output additionalContext (may work in some contexts)
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "⚡ IMMEDIATELY PROCEED TO STAGE 1: EXECUTION. Parse the execution plan JSON and begin delegating phases. DO NOT STOP."
                }
            }
            print(json.dumps(output))

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug(f"Error: {e}")


if __name__ == "__main__":
    main()
