#!/usr/bin/env python3
"""
Prompts for distillation after Task tool completion
Maintains clean orchestrator context
"""

import json
import os
import sys
from datetime import datetime


def main():
    try:
        data = json.loads(sys.stdin.read())
        tool_name = data.get("tool", "")

        # Only process Task completions in orchestration mode
        if tool_name != "Task" or os.environ.get("ORCHESTRATION_MODE") != "active":
            sys.exit(0)

        # Track task completion
        session_id = os.environ.get("SESSION_ID", "unknown")
        task_count = os.environ.get("DELEGATION_COUNT", "0")

        # Set environment variable for distillation prompt
        os.environ["NEEDS_DISTILLATION"] = "true"
        os.environ["LAST_TASK_COMPLETED"] = datetime.now().isoformat()

        # Provide distillation reminder via system-reminder (output to stdout for Claude)
        sys.stdout.write(f"""
<system-reminder>
📊 TASK COMPLETED - Distillation Required

Session: {session_id}
Task #{task_count} has completed.

Please distill the essential insights:
1. Key findings and results
2. Critical decisions or changes made
3. Any warnings or issues to track
4. Next steps or dependencies

Keep orchestrator context focused on outcomes, not implementation details.
</system-reminder>
""")
        sys.stdout.flush()

    except (json.JSONDecodeError, KeyError, ValueError):
        # Don't interfere on parsing errors
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
