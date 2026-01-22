#!/usr/bin/env python3
"""
PostToolUse Hook: Remind to update todo list after Task tool completions (cross-platform)

Analyzes todo state and provides friendly reminder for incomplete todos.

This Python version works on Windows, macOS, and Linux.
"""

import json
import os
import sys
from pathlib import Path


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

    # Determine project directory
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))

    # Check if todo state file exists
    todo_state_file = project_dir / ".claude" / "state" / "todos.json"

    if not todo_state_file.exists():
        # No todo file means no todos to track - exit silently
        return 0

    # Parse todo state and analyze completion status
    try:
        todo_data = json.loads(todo_state_file.read_text(encoding="utf-8"))
        todos = todo_data.get("todos", [])

        if not todos:
            return 0

        pending = sum(1 for t in todos if t.get("status") == "pending")
        in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
        completed = sum(1 for t in todos if t.get("status") == "completed")
        total = len(todos)
        incomplete = pending + in_progress

    except (json.JSONDecodeError, OSError):
        return 0

    # Display reminder if there are incomplete todos
    if incomplete > 0:
        print("", file=sys.stderr)
        print(f"📋 Reminder: You have {incomplete} incomplete todo(s) out of {total} total.", file=sys.stderr)

        if in_progress > 0 and pending > 0:
            print(f"   ({in_progress} in progress, {pending} pending)", file=sys.stderr)
        elif in_progress > 0:
            print(f"   ({in_progress} in progress)", file=sys.stderr)
        elif pending > 0:
            print(f"   ({pending} pending)", file=sys.stderr)

        print("   Consider updating your todo list with TodoWrite.", file=sys.stderr)
        print("", file=sys.stderr)

    # Always exit 0 to allow tool execution to proceed
    return 0


if __name__ == "__main__":
    sys.exit(main())
