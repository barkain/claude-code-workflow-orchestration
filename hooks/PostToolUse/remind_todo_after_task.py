#!/usr/bin/env python3
"""
PostToolUse Hook: Remind to update task list after Task tool completions (cross-platform)

Provides a reminder to update task status using the Tasks API after delegation completes.

This Python version works on Windows, macOS, and Linux.
"""

import io
import json
import sys

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    """Main entry point."""
    # Parse hook input from stdin
    try:
        json_input = sys.stdin.read()
        data = json.loads(json_input) if json_input else {}
    except json.JSONDecodeError:
        return 0

    # Extract tool_name
    tool_name = data.get("tool_name", "")

    # Only process Task tool invocations
    if tool_name not in ("Task", "SubagentTask", "AgentTask"):
        return 0

    # Display reminder to update task status using Tasks API
    # Note: The Tasks API manages state internally, so we provide a generic reminder
    msg = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REMINDER: Update task status with Tasks API
   Use TaskUpdate to mark completed tasks
   Use TaskList to view remaining tasks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    sys.stderr.write(msg)
    sys.stderr.flush()

    # Always exit 0 to allow tool execution to proceed
    return 0


if __name__ == "__main__":
    sys.exit(main())
