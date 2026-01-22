#!/usr/bin/env python3
"""
SessionStart Hook: Inject output style (cross-platform)

Outputs the technical-adaptive markdown content as additionalContext.
This Python version works on Windows, macOS, and Linux.
"""

import json
import os
import sys
from pathlib import Path


def get_plugin_root() -> Path:
    """Resolve plugin directory (works both in development and when installed)."""
    if plugin_root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return Path(plugin_root)
    # Fallback: navigate from hooks/SessionStart/ up to plugin root
    return Path(__file__).resolve().parent.parent.parent


def main() -> int:
    """Main entry point."""
    plugin_dir = get_plugin_root()
    output_style_path = plugin_dir / "output-styles" / "technical-adaptive.md"

    if not output_style_path.exists():
        # Exit gracefully if file doesn't exist - don't block session startup
        print(f"Warning: {output_style_path} not found", file=sys.stderr)
        return 0

    try:
        content = output_style_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Warning: Failed to read {output_style_path}: {e}", file=sys.stderr)
        return 0

    # Output JSON with escaped content for hookSpecificOutput
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
