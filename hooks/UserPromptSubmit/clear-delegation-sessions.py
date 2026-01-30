#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Clear Delegation Sessions (cross-platform)

Purpose: Clear stale delegation session state on every user prompt.
This hook ensures that delegation state doesn't persist across user
interactions, forcing explicit /delegate usage for each workflow.

Timing: Fires BEFORE each user message is processed by Claude Code

This Python version works on Windows, macOS, and Linux.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Debug mode
DEBUG_HOOK = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
DEBUG_FILE = (
    Path("/tmp/delegation_hook_debug.log")  # noqa: S108
    if os.name != "nt"
    else Path(os.environ.get("TEMP", ".")) / "delegation_hook_debug.log"
)

# Configuration
MAX_LOG_SIZE = 1048576  # 1MB threshold for log rotation
MAX_ROTATIONS = 5  # Keep 5 backup copies
VALIDATION_FILE_MAX_AGE_HOURS = 24  # Delete validation files older than 24 hours


def debug_log(message: str) -> None:
    """Write debug message if debugging is enabled."""
    if DEBUG_HOOK:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with DEBUG_FILE.open("a", encoding="utf-8") as f:
                f.write(f"[UserPromptSubmit] {timestamp} - {message}\n")
        except OSError:
            pass


def get_state_dir() -> Path:
    """Get the state directory path."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    return project_dir / ".claude" / "state"


def rotate_log(log_file: Path) -> None:
    """Rotate log file when it exceeds size threshold."""
    if not log_file.exists():
        debug_log(f"Log rotation skipped: {log_file} does not exist")
        return

    file_size = log_file.stat().st_size
    if file_size < MAX_LOG_SIZE:
        debug_log(f"Log rotation not needed: {log_file} ({file_size} bytes < {MAX_LOG_SIZE} threshold)")
        return

    debug_log(f"Rotating log file: {log_file} ({file_size} bytes >= {MAX_LOG_SIZE} threshold)")

    # Rotate existing backups
    for i in range(MAX_ROTATIONS - 1, 0, -1):
        old_backup = log_file.with_suffix(f".{i}")
        new_backup = log_file.with_suffix(f".{i + 1}")

        if old_backup.exists():
            if i == MAX_ROTATIONS - 1:
                new_backup.unlink(missing_ok=True)
                debug_log(f"Deleted oldest rotation: {new_backup}")
            try:
                old_backup.rename(new_backup)
                debug_log(f"Rotated: {old_backup} -> {new_backup}")
            except OSError:
                pass

    # Move current log to .1
    try:
        log_file.rename(log_file.with_suffix(".1"))
        log_file.touch()
        debug_log(f"Log rotation completed: {log_file} -> {log_file.with_suffix('.1')}")
    except OSError as e:
        debug_log(f"WARNING: Failed to rotate log file: {e}")


def cleanup_old_validations(validation_dir: Path) -> None:
    """Cleanup old validation state files."""
    if not validation_dir.exists():
        debug_log(f"Validation cleanup skipped: {validation_dir} does not exist")
        return

    debug_log(f"Starting validation state cleanup in: {validation_dir}")

    cutoff_time = datetime.now() - timedelta(hours=VALIDATION_FILE_MAX_AGE_HOURS)
    deleted_count = 0

    for file_path in validation_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
                debug_log(f"Deleted old validation file: {file_path}")
        except OSError as e:
            debug_log(f"WARNING: Failed to process {file_path}: {e}")

    debug_log(f"Validation cleanup completed: deleted {deleted_count} files older than {VALIDATION_FILE_MAX_AGE_HOURS}h")


def record_turn_start_timestamp(state_dir: Path) -> None:
    """Record the timestamp when user prompt is submitted.

    This is used by the stop hook to calculate turn duration.
    """
    timestamp_file = state_dir / "turn_start_timestamp.txt"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        timestamp_file.write_text(str(datetime.now().timestamp()), encoding="utf-8")
        debug_log(f"Recorded turn start timestamp: {timestamp_file}")
    except OSError as e:
        debug_log(f"WARNING: Failed to record turn start timestamp: {e}")


def main() -> int:
    """Main entry point."""
    state_dir = get_state_dir()
    delegated_sessions_file = state_dir / "delegated_sessions.txt"
    delegation_flag_file = state_dir / "delegation_active"
    active_delegations_file = state_dir / "active_delegations.json"
    validation_dir = state_dir / "validation"
    gate_log_file = validation_dir / "gate_invocations.log"
    delegation_disabled_file = state_dir / "delegation_disabled"

    # Always record turn start timestamp (for duration tracking)
    # This happens before any bypass checks so we always track timing
    record_turn_start_timestamp(state_dir)

    # Emergency bypass
    if os.environ.get("DELEGATION_HOOK_DISABLE", "0") == "1":
        debug_log("Hook disabled via DELEGATION_HOOK_DISABLE=1")
        return 0

    # Check for in-session delegation disable flag (do not clear this flag - it persists)
    if delegation_disabled_file.exists():
        debug_log("[DEBUG] Delegation disabled via flag file, skipping session clearing")
        return 0

    debug_log("Starting session cleanup and memory management")

    # 1. Clear delegation sessions
    if delegated_sessions_file.exists():
        try:
            delegated_sessions_file.unlink()
            debug_log(f"SUCCESS: Cleared delegation sessions file: {delegated_sessions_file}")
        except OSError as e:
            debug_log(f"WARNING: Failed to remove file: {e}")
            return 0
    else:
        debug_log("INFO: No delegation sessions file to clear (already clean)")

    # 1.5. Clear delegation flag for subagent session inheritance
    if delegation_flag_file.exists():
        try:
            delegation_flag_file.unlink()
            debug_log(f"SUCCESS: Cleared delegation_active flag: {delegation_flag_file}")
        except OSError as e:
            debug_log(f"WARNING: Failed to remove delegation_active flag: {e}")

    # 2. Prune stale active delegations
    if active_delegations_file.exists():
        try:
            active_delegations_file.unlink()
            debug_log("Cleared active delegations file (all sessions invalidated)")
        except OSError as e:
            debug_log(f"WARNING: Failed to clear active delegations file: {e}")

    # 3. Rotate gate invocations log if needed
    rotate_log(gate_log_file)

    # 4. Cleanup old validation state files
    cleanup_old_validations(validation_dir)

    debug_log("Session cleanup and memory management completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
