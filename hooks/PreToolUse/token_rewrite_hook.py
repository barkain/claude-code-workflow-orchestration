#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
PreToolUse Hook: Token Efficiency Rewrite (cross-platform)

Routes specific Bash commands through compact_run.py for output compression.
Only intercepts commands that benefit from post-processing (success compression,
log dedup, test failure extraction). Everything else passes through unchanged.

This hook is a rewrite-only hook — it never blocks tools (always exits 0).
Subagents are NOT skipped, as they benefit from output compression too.

Gated by CLAUDE_TOKEN_EFFICIENCY env var (default: "1", set "0" to disable).

EXIT CODES:
- 0: Always (rewrite only, never block)
"""

import io
import json
import os
import shlex
import sys
from pathlib import Path

# Force UTF-8 output on Windows (fixes encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Shell metacharacters that indicate compound commands (unsafe to wrap).
# Includes redirection operators (>, >>) which change semantics when wrapped,
# backticks for command substitution, and & for background execution.
_SHELL_META = ("|", "&&", "||", ";", "<<", "$(", ">", "`", "&")

# Command families and their subcommands that should be wrapped.
# None means the command is always wrapped regardless of subcommand.
_COMMAND_FAMILIES: dict[str, list[str] | None] = {
    "git": ["push", "pull", "fetch", "add", "commit", "merge", "rebase", "stash"],
    "docker": ["logs"],
    "podman": ["logs"],
    "kubectl": ["logs"],
    "pytest": None,
    "py.test": None,
    "cargo": ["test"],
    "npm": ["test"],
    "pnpm": ["test"],
    "yarn": ["test"],
    "bun": ["test"],
    "npx": ["vitest", "jest", "mocha", "playwright", "eslint", "next", "tsc"],  # filtered by _npx_safe()

    "go": ["test"],
    "make": ["test", "check"],
    "next": ["lint"],
}


def get_plugin_root() -> Path:
    """Resolve plugin directory (works both in development and when installed)."""
    if plugin_root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return Path(plugin_root)
    return Path(__file__).resolve().parent.parent.parent


def _normalize_cmd(token: str) -> str:
    """Normalize a command token: strip path and .exe suffix for cross-platform matching."""
    base = os.path.basename(token)
    name, ext = os.path.splitext(base)
    return name.lower() if ext.lower() == ".exe" else base


def _npx_safe(parts: list[str]) -> bool:
    """Check if an npx command is safe to wrap (not long-running).

    Long-running commands like ``npx next dev``, ``npx next start``,
    ``npx next build``, and ``npx tsc --watch`` must NOT be wrapped.
    """
    if len(parts) < 2:
        return False
    tool = parts[1]
    third = parts[2] if len(parts) > 2 else ""
    if tool == "next":
        # Only `next lint` is safe; dev/start/build are long-running
        return third == "lint"
    if tool == "tsc":
        # tsc is safe unless --watch is present anywhere
        return "--watch" not in parts and "-w" not in parts
    # vitest, jest, mocha, playwright, eslint — always safe
    return tool in ("vitest", "jest", "mocha", "playwright", "eslint")


def _should_wrap(command: str) -> bool:
    """Check if command matches a wrappable command family."""
    parts = command.split()
    if not parts:
        return False

    first = _normalize_cmd(parts[0])
    second = parts[1] if len(parts) > 1 else ""

    if first not in _COMMAND_FAMILIES:
        return False
    subcommands = _COMMAND_FAMILIES[first]
    if subcommands is None:
        # Entry exists with None value — always wrap (e.g., pytest)
        return True
    if first == "npx" and second in subcommands:
        return _npx_safe(parts)
    return second in subcommands


def _has_shell_meta(command: str) -> bool:
    """Check if command contains shell metacharacters that prevent wrapping."""
    return any(meta in command for meta in _SHELL_META)


def _extract_cd_prefix(command: str) -> tuple[str, str] | None:
    """Extract 'cd <path> && ' prefix from command, return (prefix, rest) or None."""
    import re

    m = re.match(r"^(cd\s+\S+\s*&&\s*)", command)
    if m:
        return m.group(1), command[m.end() :]
    return None


def main() -> int:
    """Main entry point."""
    # Check gate
    if os.environ.get("CLAUDE_TOKEN_EFFICIENCY", "1") == "0":
        return 0

    # Read and parse stdin JSON
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data:
            return 0
        data = json.loads(stdin_data)
    except (json.JSONDecodeError, OSError):
        return 0

    # Only intercept Bash tool
    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    # Extract command
    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not command:
        return 0

    # Skip if already wrapped
    if "compact_run.py" in command:
        return 0

    # Skip if shell metacharacters present
    if _has_shell_meta(command):
        # Special case: cd <path> && <command> — extract and check the command portion
        cd_match = _extract_cd_prefix(command)
        if cd_match:
            prefix, rest = cd_match
            if not _has_shell_meta(rest) and _should_wrap(rest):
                compact_run = get_plugin_root() / "hooks" / "compact_run.py"
                compact_run_quoted = shlex.quote(str(compact_run))
                result = {
                    "updatedInput": {
                        "command": f"{prefix}uv run --no-project --script {compact_run_quoted} {rest}"
                    }
                }
                print(json.dumps(result))  # noqa: T201
        return 0

    # Check if command should be wrapped
    if not _should_wrap(command):
        return 0

    # Build compact_run.py path
    compact_run = get_plugin_root() / "hooks" / "compact_run.py"

    # Emit rewritten command — use uv run for cross-platform Python execution
    # Shell-quote the path to handle spaces in plugin install paths
    compact_run_quoted = shlex.quote(str(compact_run))
    result = {
        "updatedInput": {
            "command": f"uv run --no-project --script {compact_run_quoted} {command}"
        }
    }
    print(json.dumps(result))  # noqa: T201

    return 0


if __name__ == "__main__":
    sys.exit(main())
