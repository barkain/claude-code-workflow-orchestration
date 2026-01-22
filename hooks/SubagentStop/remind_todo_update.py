#!/usr/bin/env python3
"""
SubagentStop Hook: Remind to update todo list (cross-platform)

Triggers when a subagent completes execution.

This Python version works on Windows, macOS, and Linux.
"""

import io
import os
import sys

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    """Main entry point."""
    # Get subagent info from environment
    subagent_type = os.environ.get("SUBAGENT_TYPE", "unknown")
    subagent_status = os.environ.get("SUBAGENT_STATUS", "completed")

    # Only remind on successful completion
    if subagent_status == "completed":
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📋 REMINDER: Update TodoWrite task list")
        print(f"   Subagent ({subagent_type}) completed successfully")
        print("   Mark current task as 'completed'")
        print("   Update next task to 'in_progress' (if multi-step)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("")

        # Remind about dependency graph for orchestrator
        if subagent_type == "delegation-orchestrator" or "orchestrat" in subagent_type:
            print("REQUIRED: Render DEPENDENCY GRAPH using box format. Do NOT skip. Prefer parallel waves.")
            print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
