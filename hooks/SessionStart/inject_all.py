#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
SessionStart Hook: Consolidated injection (cross-platform)

Combines all SessionStart hooks into a single script to avoid
3x Python startup overhead (~0.3s each via uv run).

Injects:
1. Orchestrator routing stub (orchestrator_stub.md)
2. Output style (technical-adaptive.md)
3. Token-efficient CLI guidelines (token_efficient_cli.md, gated by env var)
"""

import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows (fixes encoding errors)
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
            pass


def get_plugin_root() -> Path:
    """Resolve plugin directory (works both in development and when installed)."""
    if plugin_root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return Path(plugin_root)
    # Fallback: navigate from hooks/SessionStart/ up to plugin root
    return Path(__file__).resolve().parent.parent.parent


def read_file_safe(path: Path, label: str) -> str | None:
    """Read a file, returning None on any error."""
    if not path.exists():
        debug_log(f"{label}: not found at {path}")
        return None
    try:
        content = path.read_text(encoding="utf-8")
        debug_log(f"{label}: loaded ({len(content)} bytes)")
        return content
    except OSError as e:
        debug_log(f"{label}: read error: {e}")
        return None


def find_orchestrator_stub(plugin_dir: Path) -> str | None:
    """Locate and read orchestrator_stub.md with priority order."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))

    search_paths = [
        plugin_dir / "system-prompts" / "orchestrator_stub.md",
        Path.home() / ".claude" / "system-prompts" / "orchestrator_stub.md",
        project_dir / "system-prompts" / "orchestrator_stub.md",
        project_dir / ".claude" / "system-prompts" / "orchestrator_stub.md",
    ]

    for path in search_paths:
        if content := read_file_safe(path, "orchestrator_stub"):
            return content

    logger.warning(
        "orchestrator_stub.md not found. "
        "Multi-step workflow orchestration will not be available. "
        "Expected: %s or %s. To install: cp -r system-prompts ~/.claude/",
        plugin_dir / "system-prompts" / "orchestrator_stub.md",
        Path.home() / ".claude" / "system-prompts" / "orchestrator_stub.md",
    )
    return None


def main() -> int:
    """Main entry point."""
    debug_log(f"=== SessionStart Consolidated Hook: {__file__} ===")

    plugin_dir = get_plugin_root()
    debug_log(f"PLUGIN_DIR: {plugin_dir}")

    # Collect all context pieces
    parts: list[str] = []

    # 1. Orchestrator stub
    if content := find_orchestrator_stub(plugin_dir):
        parts.append(content)

    # 2. Output style
    if content := read_file_safe(
        plugin_dir / "output-styles" / "technical-adaptive.md",
        "output-style",
    ):
        parts.append(content)

    # 3. Token efficiency (gated by env var, default: enabled)
    if os.environ.get("CLAUDE_TOKEN_EFFICIENCY", "1") != "0":
        if content := read_file_safe(
            plugin_dir / "system-prompts" / "token_efficient_cli.md",
            "token-efficiency",
        ):
            parts.append(content)

    if not parts:
        debug_log("No content to inject")
        return 0

    # Merge all parts into a single additionalContext
    merged = "\n\n".join(parts)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": merged,
        }
    }
    sys.stdout.write(json.dumps(output))

    debug_log(
        f"SessionStart consolidated hook: injected {len(parts)} sections ({len(merged)} bytes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
