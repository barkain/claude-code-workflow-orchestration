#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Per-Turn State Reset (cross-platform)

Resets per-turn state at the start of each user prompt:
- Records turn-start timestamp (used by stop hook for duration tracking)
- Clears delegation_violations.json (fresh per-turn nudge counter)
- Clears team mode state files (team_mode_active, team_config.json)
- Clears delegation_active flag
- Rotates the gate invocations log if oversized
- Cleans up old validation state files (>24h)

This Python version works on Windows, macOS, and Linux.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

MAX_LOG_SIZE = 1048576  # 1MB
MAX_ROTATIONS = 5
VALIDATION_FILE_MAX_AGE_HOURS = 24


def get_state_dir() -> Path:
    """Get the state directory path."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    return project_dir / ".claude" / "state"


def record_turn_start_timestamp(state_dir: Path) -> None:
    """Record the timestamp when user prompt is submitted (for duration tracking)."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "turn_start_timestamp.txt").write_text(
            str(datetime.now().timestamp()), encoding="utf-8"
        )
    except OSError:
        pass


def reset_violations_counter(state_dir: Path) -> None:
    """Initialize a fresh per-turn violations counter."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        turn_id = str(datetime.now().timestamp())
        (state_dir / "delegation_violations.json").write_text(
            f'{{"violations": 0, "delegations": 0, "turn_id": "{turn_id}"}}',
            encoding="utf-8",
        )
    except OSError:
        pass


def clear_files(state_dir: Path, names: list[str]) -> None:
    """Best-effort delete of named state files."""
    for name in names:
        try:
            (state_dir / name).unlink(missing_ok=True)
        except OSError:
            pass


def rotate_log(log_file: Path) -> None:
    """Rotate log file when it exceeds size threshold."""
    if not log_file.exists() or log_file.stat().st_size < MAX_LOG_SIZE:
        return
    for i in range(MAX_ROTATIONS - 1, 0, -1):
        old_backup = log_file.with_suffix(f".{i}")
        new_backup = log_file.with_suffix(f".{i + 1}")
        if old_backup.exists():
            if i == MAX_ROTATIONS - 1:
                new_backup.unlink(missing_ok=True)
            try:
                old_backup.rename(new_backup)
            except OSError:
                pass
    try:
        log_file.rename(log_file.with_suffix(".1"))
        log_file.touch()
    except OSError:
        pass


def cleanup_old_validations(validation_dir: Path) -> None:
    """Delete validation state files older than VALIDATION_FILE_MAX_AGE_HOURS."""
    if not validation_dir.exists():
        return
    cutoff = datetime.now() - timedelta(hours=VALIDATION_FILE_MAX_AGE_HOURS)
    for file_path in validation_dir.glob("*.json"):
        try:
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
                file_path.unlink()
        except OSError:
            pass


def main() -> int:
    """Main entry point."""
    state_dir = get_state_dir()

    record_turn_start_timestamp(state_dir)
    reset_violations_counter(state_dir)

    clear_files(
        state_dir,
        [
            "delegation_active",
            "active_delegations.json",
            "team_mode_active",
            "team_config.json",
        ],
    )

    rotate_log(state_dir / "validation" / "gate_invocations.log")
    cleanup_old_validations(state_dir / "validation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
