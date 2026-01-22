#!/usr/bin/env python3
"""
SessionStart Hook: Inject workflow_orchestrator system prompt (cross-platform)

This hook runs on session startup/resume/clear/compact and injects the
workflow_orchestrator.md system prompt into Claude's context. This enables
automatic multi-step workflow detection, phase decomposition, and intelligent
delegation orchestration for every session.

This Python version works on Windows, macOS, and Linux.
"""

import io
import json
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Debug mode
DEBUG_HOOK = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
DEBUG_FILE = Path("/tmp/delegation_hook_debug.log") if os.name != "nt" else Path(os.environ.get("TEMP", ".")) / "delegation_hook_debug.log"


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
    Locate workflow_orchestrator.md with priority order:
    1. Plugin directory (marketplace or development install)
    2. Installed location: ~/.claude/system-prompts/workflow_orchestrator.md
    3. Repository src/ location (for development)
    4. Local .claude directory (project-specific override)
    """
    plugin_dir = get_plugin_root()
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))

    search_paths = [
        plugin_dir / "system-prompts" / "workflow_orchestrator.md",
        Path.home() / ".claude" / "system-prompts" / "workflow_orchestrator.md",
        project_dir / "system-prompts" / "workflow_orchestrator.md",
        project_dir / ".claude" / "system-prompts" / "workflow_orchestrator.md",
    ]

    for path in search_paths:
        if path.exists():
            debug_log(f"Found orchestrator at: {path}")
            return path

    return None


def main() -> int:
    """Main entry point."""
    debug_log(f"=== SessionStart Hook (Python): {__file__} ===")
    debug_log(f"PLUGIN_DIR: {get_plugin_root()}")

    orchestrator_file = find_orchestrator_file()

    if orchestrator_file is None:
        # File not found - log error and exit gracefully
        # Don't block session startup, but warn user
        print("⚠️ Warning: workflow_orchestrator.md not found", file=sys.stderr)
        print("", file=sys.stderr)
        print("Multi-step workflow orchestration will not be available.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Expected locations:", file=sys.stderr)
        print(f"  - {get_plugin_root() / 'system-prompts' / 'workflow_orchestrator.md'}", file=sys.stderr)
        print(f"  - {Path.home() / '.claude' / 'system-prompts' / 'workflow_orchestrator.md'}", file=sys.stderr)
        print("", file=sys.stderr)
        print("To install: cp -r system-prompts ~/.claude/", file=sys.stderr)

        debug_log("ERROR: workflow_orchestrator.md not found")
        return 0  # Exit gracefully - don't block session startup

    try:
        content = orchestrator_file.read_text(encoding="utf-8")
        line_count = content.count("\n") + 1
        byte_count = len(content.encode("utf-8"))
        debug_log(f"Injecting workflow_orchestrator.md ({line_count} lines, {byte_count} bytes)")
    except OSError as e:
        print(f"⚠️ Warning: Failed to read {orchestrator_file}: {e}", file=sys.stderr)
        debug_log(f"ERROR: Failed to read file: {e}")
        return 0

    # Output JSON with escaped content for hookSpecificOutput
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }
    print(json.dumps(output))

    debug_log("SessionStart hook completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
