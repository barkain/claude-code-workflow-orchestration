#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
SessionStart Hook: Inject orchestrator routing stub (cross-platform)

This hook runs on session startup/resume/clear/compact and injects the
orchestrator_stub.md routing prompt into Claude's context. The full
workflow_orchestrator.md is loaded on-demand by /workflow-orchestrator:delegate.

This Python version works on Windows, macOS, and Linux.
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

logger = logging.getLogger(__name__)

# Debug mode
DEBUG_HOOK = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
DEBUG_FILE = Path(tempfile.gettempdir()) / "delegation_hook_debug.log"


def debug_log(message: str) -> None:
    """Write debug message if debugging is enabled."""
    if DEBUG_HOOK:
        try:
            with DEBUG_FILE.open("a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except OSError:
            pass  # Ignore debug logging failures


def get_plugin_root() -> Path:
    """Resolve plugin directory (works both in development and when installed)."""
    if plugin_root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return Path(plugin_root)
    # Fallback: navigate from hooks/SessionStart/ up to plugin root
    return Path(__file__).resolve().parent.parent.parent


def find_orchestrator_file() -> Path | None:
    """
    Locate orchestrator_stub.md (lightweight routing stub) with priority order:
    1. Plugin directory (marketplace or development install)
    2. Installed location: ~/.claude/system-prompts/orchestrator_stub.md
    3. Repository src/ location (for development)
    4. Local .claude directory (project-specific override)

    The full workflow_orchestrator.md is loaded on-demand by /workflow-orchestrator:delegate.
    """
    plugin_dir = get_plugin_root()
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))

    search_paths = [
        plugin_dir / "system-prompts" / "orchestrator_stub.md",
        Path.home() / ".claude" / "system-prompts" / "orchestrator_stub.md",
        project_dir / "system-prompts" / "orchestrator_stub.md",
        project_dir / ".claude" / "system-prompts" / "orchestrator_stub.md",
    ]

    for path in search_paths:
        if path.exists():
            debug_log(f"Found orchestrator stub at: {path}")
            return path

    return None


def main() -> int:
    """Main entry point."""
    debug_log(f"=== SessionStart Hook (Python): {__file__} ===")
    debug_log(f"PLUGIN_DIR: {get_plugin_root()}")

    orchestrator_file = find_orchestrator_file()

    if orchestrator_file is None:
        logger.warning(
            "orchestrator_stub.md not found. "
            "Multi-step workflow orchestration will not be available. "
            "Expected: %s or %s. To install: cp -r system-prompts ~/.claude/",
            get_plugin_root() / "system-prompts" / "orchestrator_stub.md",
            Path.home() / ".claude" / "system-prompts" / "orchestrator_stub.md",
        )

        debug_log("ERROR: orchestrator_stub.md not found")
        return 0  # Exit gracefully - don't block session startup

    try:
        content = orchestrator_file.read_text(encoding="utf-8")
        line_count = content.count("\n") + 1
        byte_count = len(content.encode("utf-8"))
        debug_log(
            f"Injecting orchestrator_stub.md ({line_count} lines, {byte_count} bytes)"
        )
    except OSError as e:
        logger.warning("Failed to read %s: %s", orchestrator_file, e)
        debug_log(f"ERROR: Failed to read file: {e}")
        return 0

    # Output JSON with escaped content for hookSpecificOutput
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }
    sys.stdout.write(json.dumps(output))

    debug_log("SessionStart hook completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
