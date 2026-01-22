#!/usr/bin/env python3
"""
SubagentStop Hook: Trigger verification (cross-platform)

Triggers verification after agent completion.

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
    # Get agent info from environment
    agent_type = os.environ.get("AGENT_TYPE", "unknown")
    agent_status = os.environ.get("AGENT_STATUS", "completed")

    # Only trigger on successful completion
    if agent_status != "completed":
        return 0

    # Skip for specific agents to avoid recursion
    if agent_type in ("task-completion-verifier", "delegation-orchestrator"):
        return 0

    # Output brief verification instruction
    print(f"🔍 Spawn task-completion-verifier to verify the work completed by {agent_type}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
