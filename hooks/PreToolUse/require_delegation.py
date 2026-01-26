#!/usr/bin/env python3
"""
PreToolUse Hook: Require Delegation (cross-platform)

Block tools unless /delegate was used, but ALWAYS allow delegation tools.
Tool name is passed via stdin as JSON.

This Python version works on Windows, macOS, and Linux.

EXIT CODES:
- 0: Allow the tool
- 2: Block the tool (non-zero blocks in Claude Code hooks)
"""

import io
import json
import os
import re
import sys
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Debug mode
DEBUG_HOOK = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
DEBUG_FILE = (
    Path("/tmp/delegation_hook_debug.log")
    if os.name != "nt"
    else Path(os.environ.get("TEMP", ".")) / "delegation_hook_debug.log"
)


def debug_log(message: str) -> None:
    """Write debug message if debugging is enabled."""
    if DEBUG_HOOK:
        try:
            with DEBUG_FILE.open("a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except OSError:
            pass


def get_state_dir() -> Path:
    """Get the state directory path."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    state_dir = project_dir / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


# Allowlist of tools that don't require delegation
ALLOWED_TOOLS = {
    "AskUserQuestion",
    # Tasks API tools (replaces deprecated TodoWrite)
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "TaskGet",
    "Skill",  # Claude Code 70+ tool name for slash commands
    "SlashCommand",  # Deprecated: Keep for backwards compatibility
    "Task",  # Allow delegation Task tool
    "SubagentTask",
    "AgentTask",
}


def block_tool(tool_name: str) -> int:
    """Block a tool and print the error message."""
    if not tool_name:
        print("🚫 Tool blocked by delegation policy", file=sys.stderr)
        print("Tool: <unknown - failed to parse>", file=sys.stderr)
        print("", file=sys.stderr)
        print("⚠️ STOP: Do NOT try alternative tools.", file=sys.stderr)
        print("✅ REQUIRED: Use /delegate command immediately:", file=sys.stderr)
        print("   /delegate <full task description>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Debug: export DEBUG_DELEGATION_HOOK=1", file=sys.stderr)
    else:
        print("🚫 Tool blocked by delegation policy", file=sys.stderr)
        print(f"Tool: {tool_name}", file=sys.stderr)
        print("", file=sys.stderr)
        print("⚠️ STOP: Do NOT try alternative tools.", file=sys.stderr)
        print("✅ REQUIRED: Use /delegate command immediately:", file=sys.stderr)
        print("   /delegate <full task description>", file=sys.stderr)
    return 2


def main() -> int:
    """Main entry point."""
    debug_log("=== PreToolUse Hook START ===")

    state_dir = get_state_dir()
    delegated_sessions_file = state_dir / "delegated_sessions.txt"
    delegation_flag = state_dir / "delegation_active"
    flag_file = state_dir / "delegated.once"
    delegation_disabled_file = state_dir / "delegation_disabled"

    debug_log(f"State dir: {state_dir}")
    debug_log(f"delegation_disabled exists: {delegation_disabled_file.exists()}")
    debug_log(f"delegation_active exists: {delegation_flag.exists()}")

    # Quick bypass for emergencies
    if os.environ.get("DELEGATION_HOOK_DISABLE", "0") == "1":
        debug_log("Hook disabled via DELEGATION_HOOK_DISABLE")
        return 0

    # Check for in-session delegation disable flag
    if delegation_disabled_file.exists():
        debug_log("[DEBUG] Delegation disabled via flag file, allowing all tools")
        return 0

    # Read stdin JSON
    stdin_data = ""
    try:
        stdin_data = sys.stdin.read()
        debug_log(f"Stdin data: {stdin_data[:500] if stdin_data else '<empty>'}")
    except Exception as e:
        debug_log(f"Failed to read stdin: {e}")
        # If we can't read stdin, block by default for safety
        return block_tool("")

    # Parse JSON to extract tool_name and session_id
    tool_name = ""
    session_id = ""
    try:
        data = json.loads(stdin_data) if stdin_data else {}
        tool_name = data.get("tool_name", "")
        session_id = data.get("session_id", "")
    except json.JSONDecodeError:
        # Fallback: try to extract with simple string parsing
        tool_match = re.search(r'"tool_name"\s*:\s*"([^"]*)"', stdin_data)
        if tool_match:
            tool_name = tool_match.group(1)
        session_match = re.search(r'"session_id"\s*:\s*"([^"]*)"', stdin_data)
        if session_match:
            session_id = session_match.group(1)

    debug_log(f"Extracted TOOL_NAME: '{tool_name}'")
    debug_log(f"Extracted SESSION_ID: '{session_id}'")

    # Check allowlist (case-insensitive)
    if tool_name:
        tool_name_lower = tool_name.lower()
        for allowed in ALLOWED_TOOLS:
            if tool_name_lower == allowed.lower():
                debug_log(f"ALLOWED: Matched '{allowed}'")

                # If this is a Task or SlashCommand/Skill tool, mark session as delegated
                if tool_name in {"Task", "SubagentTask", "AgentTask", "SlashCommand", "Skill"}:
                    if session_id:
                        # Register session
                        existing = set()
                        if delegated_sessions_file.exists():
                            try:
                                existing = set(delegated_sessions_file.read_text().strip().split("\n"))
                            except OSError:
                                pass
                        if session_id not in existing:
                            try:
                                with delegated_sessions_file.open("a", encoding="utf-8") as f:
                                    f.write(f"{session_id}\n")
                                debug_log(f"REGISTERED: Session '{session_id}' for delegation")
                            except OSError as e:
                                debug_log(f"Failed to register session: {e}")

                        # Set delegation flag for subagent session inheritance
                        try:
                            delegation_flag.touch()
                            debug_log("FLAG: Created delegation_active for subagent inheritance")
                        except OSError as e:
                            debug_log(f"Failed to create delegation flag: {e}")

                return 0

        # Pattern allow (delegation-related)
        if "delegate" in tool_name_lower or "delegation" in tool_name_lower or tool_name.startswith("Task."):
            debug_log("ALLOWED: Delegation pattern")
            return 0

    # Check delegation flag file (one-time use)
    if flag_file.exists():
        debug_log("ALLOWED: Delegation flag found")
        try:
            flag_file.unlink()
        except OSError:
            pass
        return 0

    # Check delegation active flag (subagent session inheritance)
    if delegation_flag.exists():
        debug_log("ALLOWED: Delegation active flag exists (subagent session inheritance)")
        return 0

    # Check if current session is delegated
    if delegated_sessions_file.exists() and session_id:
        try:
            sessions = set(delegated_sessions_file.read_text().strip().split("\n"))
            if session_id in sessions:
                debug_log(f"ALLOWED: Session '{session_id}' is delegated")
                return 0
        except OSError as e:
            debug_log(f"Failed to read sessions file: {e}")

    # Block the tool
    debug_log(f"BLOCKED: Tool '{tool_name}'")
    return block_tool(tool_name)


if __name__ == "__main__":
    try:
        exit_code = main()
        debug_log(f"=== PreToolUse Hook END (exit {exit_code}) ===")
        sys.exit(exit_code)
    except Exception as e:
        # Any uncaught exception should block the tool for safety
        debug_log(f"UNCAUGHT EXCEPTION: {e}")
        print(f"🚫 Hook error: {e}", file=sys.stderr)
        print("Tool blocked due to hook error.", file=sys.stderr)
        sys.exit(2)
