#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Enhanced Claude Code Statusline with Accurate Token Tracking
Cross-platform Python version (works on Windows, macOS, Linux)
"""

import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Configuration - use system temp directory securely
DEBUG_LOG = Path(tempfile.gettempdir()) / "statusline_debug.log"


def debug_log(message: str) -> None:
    """Write debug message to log file."""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}: {message}\n")
    except OSError:
        pass


def create_progress_bar(usage_rate: float, used_tokens: int, limit_tokens: int) -> str:
    """Create a colored progress bar for context usage."""
    percentage = max(0, min(100, int(usage_rate)))

    # Calculate filled blocks (10 total)
    filled_blocks = percentage * 10 // 100
    empty_blocks = 10 - filled_blocks

    # Build bar using Unicode block characters
    filled_part = "█" * filled_blocks
    empty_part = "░" * empty_blocks

    # Format tokens with k/M suffixes
    def format_tokens(tokens: int) -> str:
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M".replace(".0M", "M")
        elif tokens >= 1000:
            return f"{tokens // 1000}k"
        return str(tokens)

    formatted_used = format_tokens(used_tokens)
    formatted_limit = format_tokens(limit_tokens)

    # Choose color based on usage rate
    if percentage >= 70:
        color_code = "\033[31m"  # Red
    elif percentage >= 60:
        color_code = "\033[33m"  # Yellow/Orange
    elif percentage >= 40:
        color_code = "\033[93m"  # Bright Yellow
    else:
        color_code = "\033[32m"  # Green
    reset_code = "\033[0m"

    formatted_percentage = f"{usage_rate:.1f}"

    return f"{color_code}[{filled_part}{empty_part}] {formatted_percentage}% ({formatted_used}/{formatted_limit}){reset_code}"


def find_session_file(session_id: str, current_dir: str) -> Path | None:
    """Find the session JSONL file."""
    home = Path.home()

    debug_log(f"Looking for session: {session_id} in dir: {current_dir}")

    # Method 1: Direct lookup in .claude/sessions
    direct_file = home / ".claude" / "sessions" / f"{session_id}.jsonl"
    if direct_file.exists():
        debug_log(f"Found session file (direct): {direct_file}")
        return direct_file

    # Method 2: Project-based lookup (with tilde replacement)
    project_dir = (
        current_dir.replace(str(home), "~")
        .replace("/", "-")
        .replace("\\", "-")
        .lstrip("-")
    )
    project_file = (
        home / ".claude" / "projects" / f"-{project_dir}" / f"{session_id}.jsonl"
    )
    if project_file.exists():
        debug_log(f"Found session file (project): {project_file}")
        return project_file

    # Method 3: Project-based lookup (without tilde)
    alt_project_dir = current_dir.replace("/", "-").replace("\\", "-").lstrip("-")
    alt_project_file = (
        home / ".claude" / "projects" / f"-{alt_project_dir}" / f"{session_id}.jsonl"
    )
    if alt_project_file.exists():
        debug_log(f"Found session file (alt project): {alt_project_file}")
        return alt_project_file

    # Method 4: Fallback - recursive search
    claude_dir = home / ".claude"
    if claude_dir.exists():
        for jsonl_file in claude_dir.rglob(f"{session_id}.jsonl"):
            debug_log(f"Found session file (recursive): {jsonl_file}")
            return jsonl_file

    debug_log(f"No session file found for {session_id}")
    return None


def calculate_context_usage(input_data: dict) -> tuple[str | None, float]:
    """Calculate actual context usage from session file.

    If ``context_window`` is present in *input_data* (provided by stdin JSON),
    it is used directly — avoiding the expensive JSONL scan entirely.

    Returns:
        Tuple of (formatted_string, raw_pct) where raw_pct is the usage
        percentage as a float (e.g. 57.1), or 0.0 if unavailable.
    """
    # --- Fast path: use context_window from stdin JSON if available ---
    ctx_window = (
        input_data.get("context_window", {}) if isinstance(input_data, dict) else {}
    )
    if isinstance(ctx_window, dict) and ctx_window:
        used = ctx_window.get("used_tokens") or ctx_window.get("used", 0)
        limit = ctx_window.get("total_tokens") or ctx_window.get("limit", 0)
        if (
            isinstance(used, (int, float))
            and isinstance(limit, (int, float))
            and limit > 0
        ):
            usage_rate = float(used) * 100 / float(limit)
            progress_bar = create_progress_bar(usage_rate, int(used), int(limit))
            debug_log(f"Context from stdin JSON: {used}/{limit} ({usage_rate:.1f}%)")
            return f"🧠 {progress_bar}", usage_rate

    # --- Slow path: scan session JSONL file ---
    session_id = input_data.get("session_id", "")
    current_dir = input_data.get("cwd") or input_data.get("workspace", {}).get(
        "current_dir", ""
    )

    debug_log(f"Session ID: {session_id}, Current Dir: {current_dir}")

    if not session_id:
        return None, 0.0

    # Determine max context based on model
    model_name = input_data.get("model", {}).get("display_name") or input_data.get(
        "model", {}
    ).get("id", "")
    max_context = 200000  # Default

    if "1M" in model_name or "1M token" in model_name:
        max_context = 1_000_000

    debug_log(f"Model: {model_name}, Max context: {max_context}")

    session_file = find_session_file(session_id, current_dir)
    if not session_file:
        return None, 0.0

    debug_log(f"Processing session file: {session_file}")

    try:
        # Read session file and find token usage
        last_reset_line = 0
        lines = []

        with open(session_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                lines.append(line)
                # Check for context reset
                if '"/clear"' in line or '"/compact"' in line:
                    last_reset_line = i

        debug_log(f"Total lines: {len(lines)}, Last reset at: {last_reset_line}")

        # Get token entries after reset
        token_entries = []
        for line in lines[last_reset_line:]:
            try:
                entry = json.loads(line)
                usage = entry.get("message", {}).get("usage", {})
                if usage:
                    token_entries.append(
                        {
                            "input": usage.get("input_tokens", 0),
                            "cache_read": usage.get("cache_read_input_tokens", 0),
                            "cache_create": usage.get("cache_creation_input_tokens", 0),
                            "output": usage.get("output_tokens", 0),
                        }
                    )
            except json.JSONDecodeError:
                continue

        debug_log(f"Token entries found: {len(token_entries)}")

        if token_entries:
            last_entry = token_entries[-1]
            total_input = (
                last_entry["input"]
                + last_entry["cache_read"]
                + last_entry["cache_create"]
            )

            debug_log(
                f"Last entry tokens - Input: {last_entry['input']}, Cache Read: {last_entry['cache_read']}, Cache Create: {last_entry['cache_create']}, Total: {total_input}"
            )

            if total_input > 0:
                usage_rate = total_input * 100 / max_context
                progress_bar = create_progress_bar(usage_rate, total_input, max_context)
                return f"🧠 {progress_bar}", usage_rate

    except OSError as e:
        debug_log(f"Error reading session file: {e}")

    return None, 0.0


def shorten_cwd(full_path: str) -> str:
    """Shorten the current working directory path."""
    home = str(Path.home())

    # Check for /dev/ pattern
    if "/dev/" in full_path or "\\dev\\" in full_path:
        after_dev = full_path.split("/dev/")[-1].split("\\dev\\")[-1]
        components = [c for c in after_dev.replace("\\", "/").split("/") if c]
        if len(components) > 2:
            return f"{components[0]}/.../{components[-1]}"
        return after_dev.replace("\\", "/")

    # Check for Projects pattern
    for pattern in ["/Projects/", "\\Projects\\", "/projects/", "\\projects\\"]:
        if pattern in full_path:
            return full_path.split(pattern)[-1].replace("\\", "/")

    # Home-relative path
    if full_path.startswith(home):
        rel_path = full_path[len(home) :].lstrip("/\\")
        components = [c for c in rel_path.replace("\\", "/").split("/") if c]
        if len(components) > 3:
            return f"~/{components[0]}/.../{components[-1]}"
        return f"~/{rel_path.replace(chr(92), '/')}"

    # Default: last component
    return f".../{Path(full_path).name}"


def truncate_str(s: str, max_len: int) -> str:
    """Truncate a string to max_len, showing start + ellipsis + end if too long."""
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]
    # Show roughly first 40% and last 50% with ellipsis
    head = max_len * 2 // 5
    tail = max_len - head - 1
    return s[:head] + "\u2026" + s[len(s) - tail :]


def get_terminal_width() -> int:
    """Get terminal width, defaulting to 120 if detection fails.

    Only falls back to 120 when detection truly fails (returns 0 or raises
    an exception). Small positive values are allowed through so narrow
    terminals get compact layouts.
    """
    try:
        import shutil

        width = shutil.get_terminal_size(fallback=(120, 24)).columns
        return width if width > 0 else 120
    except Exception:
        return 120


def get_git_branch(cwd: str | None = None) -> str:
    """Get the current git branch (raw name, no emoji)."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],  # noqa: S607, S603
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, TypeError):
        pass
    return "no-git"


def get_claude_version_cached() -> str:
    """Get Claude Code version from a cached temp file (1-hour TTL).

    Only called when stdin JSON does not provide a ``version`` field.
    """
    cache_file = Path(tempfile.gettempdir()) / "claude_version_cache.json"
    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            ts = data.get("ts", 0)
            if datetime.now().timestamp() - ts < 3600:
                return data.get("version", "v?")
    except (OSError, json.JSONDecodeError, ValueError):
        pass

    version = "v?"
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "--version"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            version_num = result.stdout.strip().split()[0]
            version = f"v{version_num}" if version_num else "v?"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    try:
        cache_file.write_text(
            json.dumps({"version": version, "ts": datetime.now().timestamp()}),
            encoding="utf-8",
        )
    except OSError:
        pass
    return version


def get_turn_duration() -> str | None:
    """Get the duration of the last completed turn.

    Reads from the state file written by the stop hook which calculates
    duration from UserPromptSubmit to Stop events.

    Returns:
        Formatted duration string like "45s" or "1m 23s", or None if not available.
    """
    state_dir = (
        Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())) / ".claude" / "state"
    )
    duration_file = state_dir / "last_turn_duration.txt"

    if not duration_file.exists():
        return None

    try:
        duration_str = duration_file.read_text(encoding="utf-8").strip()
        if duration_str:
            return duration_str
    except OSError:
        pass

    return None


def format_usage_percentages(
    five_hour_pct: float | None,
    seven_day_pct: float | None,
    compact: bool = False,
) -> str:
    """Format 5h and weekly usage as colored percentage strings.

    Uses values from the statusLine JSON stdin ``rate_limits`` field.

    Args:
        five_hour_pct: 5-hour utilization percentage (0-100) from rate_limits, or None if unavailable.
        seven_day_pct: 7-day utilization percentage (0-100) from rate_limits, or None if unavailable.
        compact: If True, use shorter labels (e.g., "5h 2%·w 60%").

    Returns:
        Formatted string like "5h 6% · weekly 1%" with ANSI color codes.
    """
    reset = "\033[0m"

    def color_for_pct(pct: float) -> str:
        if pct >= 75:
            return "\033[31m"  # Red
        elif pct >= 50:
            return "\033[33m"  # Yellow
        return "\033[32m"  # Green

    if five_hour_pct is not None:
        five_h_str = f"{five_hour_pct:.0f}%"
        five_h_color = color_for_pct(five_hour_pct)
    else:
        five_h_str = "\u2026%"
        five_h_color = "\033[90m"  # Gray for placeholder

    if seven_day_pct is not None:
        weekly_str = f"{seven_day_pct:.0f}%"
        weekly_color = color_for_pct(seven_day_pct)
    else:
        weekly_str = "\u2026%"
        weekly_color = "\033[90m"  # Gray for placeholder

    if compact:
        return (
            f"{five_h_color}5h {five_h_str}{reset}"
            f"\u00b7"
            f"{weekly_color}w {weekly_str}{reset}"
        )

    return (
        f"{five_h_color}5h {five_h_str}{reset}"
        f" \u00b7 "
        f"{weekly_color}weekly {weekly_str}{reset}"
    )


def main() -> None:
    """Main entry point."""
    # Clear debug log at start
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write(f"=== Statusline run at {datetime.now()} ===\n")
    except OSError:
        pass

    # Color codes
    SHINY_AQUA = (
        "\033[38;2;0;255;255m"  # Cyan/aqua - visible on both light and dark themes
    )
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    # Read JSON input from stdin if available
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.loads(sys.stdin.read())
            # Save for debugging
            try:
                debug_input_path = Path(tempfile.gettempdir()) / "statusline_input.json"
                with open(debug_input_path, "w") as f:
                    json.dump(input_data, f, indent=2)
            except OSError:
                pass
        except json.JSONDecodeError:
            pass

    # Get model info
    model = input_data.get("model", {})
    raw_model = model.get("display_name") or model.get("id", "Unknown")
    debug_log(f"Model: {raw_model}")

    # Get current working directory for project-based cost tracking
    # Prefer cwd from stdin JSON (reflects worktrees) over os.getcwd()
    raw_cwd = input_data.get("cwd") if isinstance(input_data, dict) else None
    effective_cwd = raw_cwd if isinstance(raw_cwd, str) and raw_cwd else os.getcwd()

    # Session cost from stdin JSON (real-time, no I/O needed)
    session_cost_usd = 0.0
    stdin_cost = input_data.get("cost", {}) if isinstance(input_data, dict) else {}
    if isinstance(stdin_cost, dict):
        raw_val = stdin_cost.get("total_cost_usd")
        if isinstance(raw_val, (int, float)):
            session_cost_usd = float(raw_val)

    cost_str = (
        f"\U0001f4b0 ${session_cost_usd:.2f}" if session_cost_usd else "\U0001f4b0 $..."
    )

    # Get Claude version — prefer stdin JSON, fall back to cached subprocess
    stdin_version = (
        input_data.get("version", "") if isinstance(input_data, dict) else ""
    )
    if stdin_version:
        # Normalize: add "v" prefix if missing
        claude_version = (
            stdin_version if stdin_version.startswith("v") else f"v{stdin_version}"
        )
    else:
        claude_version = get_claude_version_cached()

    # Get context info
    context_info, ctx_raw_pct = calculate_context_usage(input_data)
    if not context_info:
        # Fallback empty progress bar
        max_context = 200000
        if "1M" in raw_model:
            max_context = 1_000_000
        progress_bar = create_progress_bar(0, 0, max_context)
        context_info = f"🧠 {progress_bar}"

    # Get git branch (raw name) — use effective_cwd so worktrees show correct branch
    branch_raw = get_git_branch(cwd=effective_cwd)

    # Get shortened CWD
    cwd = shorten_cwd(effective_cwd)

    # Get turn duration if available
    turn_duration = get_turn_duration()

    # Format cost display
    cost_display = f"{GREEN}{cost_str}{RESET}"

    # Extract rate limits from statusLine JSON input
    rate_limits = input_data.get("rate_limits", {})
    five_hour = rate_limits.get("five_hour", {})
    seven_day = rate_limits.get("seven_day", {})
    five_hour_pct = five_hour.get("used_percentage")  # float or None
    seven_day_pct = seven_day.get("used_percentage")  # float or None

    usage_display = format_usage_percentages(five_hour_pct, seven_day_pct)

    # Detect terminal width for responsive layout
    term_width = get_terminal_width()

    # --- Row 1: version | model | dir | branch ---
    # Apply initial truncation limits
    dir_max = 25
    branch_max = 20
    cwd_trunc = truncate_str(cwd, dir_max)
    branch_trunc = truncate_str(branch_raw, branch_max)

    # Estimate visible length of row 1 (exclude ANSI codes, emoji ~2 chars each)
    # Format: "vX.X.X | 🤖 model | 📁 dir | 🌿 branch ⚡"
    def _row1_visible_len(d: str, b: str) -> int:
        return (
            len(claude_version)
            + 3  # " | "
            + 2
            + len(raw_model)  # "🤖 " + model
            + 3  # " | "
            + 2
            + len(d)  # "📁 " + dir
            + 3  # " | "
            + 2
            + len(b)
            + 2  # "🌿 " + branch + " ⚡"
        )

    # Progressive shortening if row 1 exceeds terminal width
    est_len = _row1_visible_len(cwd_trunc, branch_trunc)
    if est_len > term_width:
        # First: shorten branch more aggressively
        branch_trunc = truncate_str(
            branch_raw, max(10, branch_max - (est_len - term_width))
        )
        est_len = _row1_visible_len(cwd_trunc, branch_trunc)
    if est_len > term_width:
        # Second: shorten directory more aggressively
        cwd_trunc = truncate_str(cwd, max(10, dir_max - (est_len - term_width)))

    git_status = f"\U0001f33f {branch_trunc} \u26a1"
    cwd_display = f"{SHINY_AQUA}\U0001f4c1 {cwd_trunc}{RESET}"

    # Output Row 1
    sys.stdout.write(
        f"{BLUE}{claude_version}{RESET} | {SHINY_AQUA}\U0001f916 {raw_model}{RESET} | {cwd_display} | {YELLOW}{git_status}{RESET}\n"
    )

    # --- Row 2: context bar | usage | cost | duration ---
    # Row 2 must ALWAYS show something. At minimum: context percentage and usage.
    # Progressive compaction for narrow terminals instead of hiding elements.
    if term_width >= 100:
        # Full layout: context bar | usage | cost | duration
        row2_parts = [context_info, usage_display, cost_display]
        if turn_duration:
            row2_parts.append(f"{YELLOW}\u23f1\ufe0f {turn_duration}{RESET}")
    elif term_width >= 80:
        # Medium: context bar | usage | cost (no duration)
        row2_parts = [context_info, usage_display, cost_display]
    elif term_width >= 60:
        # Compact: context bar | compact usage (drop cost, duration)
        compact_usage = format_usage_percentages(
            five_hour_pct, seven_day_pct, compact=True
        )
        row2_parts = [context_info, compact_usage]
    else:
        # Minimal: just percentage + compact usage (drop bar, emoji, cost, duration)
        compact_usage = format_usage_percentages(
            five_hour_pct, seven_day_pct, compact=True
        )
        # Reuse raw percentage from calculate_context_usage() (no re-read)
        ctx_pct = f"{ctx_raw_pct:.0f}%"
        row2_parts = [ctx_pct, compact_usage]

    sys.stdout.write(" | ".join(row2_parts) + "\n")


if __name__ == "__main__":
    main()
