#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
SessionStart Hook: Inject token-efficient CLI usage guidelines (cross-platform)

Outputs the token-efficient CLI markdown content as additionalContext.
This Python version works on Windows, macOS, and Linux.

Gated by CLAUDE_TOKEN_EFFICIENCY env var (default: enabled).
Set CLAUDE_TOKEN_EFFICIENCY=0 to disable.
"""

import io
import json
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows (fixes encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def get_plugin_root() -> Path:
    """Resolve plugin directory (works both in development and when installed)."""
    if plugin_root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return Path(plugin_root)
    # Fallback: navigate from hooks/SessionStart/ up to plugin root
    return Path(__file__).resolve().parent.parent.parent


def main() -> int:
    """Main entry point."""
    # Gate on CLAUDE_TOKEN_EFFICIENCY env var (default: enabled)
    if os.environ.get("CLAUDE_TOKEN_EFFICIENCY", "1") == "0":
        return 0

    plugin_dir = get_plugin_root()
    token_efficiency_path = plugin_dir / "system-prompts" / "token_efficient_cli.md"

    if not token_efficiency_path.exists():
        # Exit gracefully if file doesn't exist - don't block session startup
        print(f"Warning: {token_efficiency_path} not found", file=sys.stderr)  # noqa: T201
        return 0

    try:
        content = token_efficiency_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Warning: Failed to read {token_efficiency_path}: {e}", file=sys.stderr)  # noqa: T201
        return 0

    # Output JSON with escaped content for hookSpecificOutput
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }

    print(json.dumps(output))  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
