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
import time
from datetime import datetime, timedelta
from pathlib import Path

# Cache configuration
COST_CACHE_TTL_SECONDS = 300  # Cache costs for 5 minutes (cost data changes slowly)
COST_CACHE_FILE = Path(tempfile.gettempdir()) / "statusline_cost_cache.json"
COST_REFRESH_LOCK = Path(tempfile.gettempdir()) / "statusline_cost_refresh.lock"  # noqa: S108

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

    Returns:
        Tuple of (formatted_string, raw_pct) where raw_pct is the usage
        percentage as a float (e.g. 57.1), or 0.0 if unavailable.
    """
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
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "no-git"


def load_cost_cache() -> dict:
    """Load cost cache from file.

    Returns:
        Cache dictionary with 'daily_cost', 'session_cost', 'timestamp', 'cwd' keys,
        or empty dict if cache doesn't exist or is invalid.
    """
    try:
        if COST_CACHE_FILE.exists():
            return json.loads(COST_CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_cost_cache(
    daily_cost: str,
    session_cost: str,
    cwd: str,
    daily_cost_val: float = 0.0,
    weekly_cost_val: float = 0.0,
) -> None:
    """Save cost values to cache file.

    Args:
        daily_cost: Formatted daily cost string.
        session_cost: Formatted session cost string.
        cwd: Current working directory (for cache invalidation).
        daily_cost_val: Raw daily cost value for percentage calculations.
        weekly_cost_val: Raw weekly cost value for percentage calculations.
    """
    cache = {
        "daily_cost": daily_cost,
        "session_cost": session_cost,
        "daily_cost_val": daily_cost_val,
        "weekly_cost_val": weekly_cost_val,
        "timestamp": time.time(),
        "cwd": cwd,
    }
    try:
        COST_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass


def is_cache_valid(cache: dict, cwd: str) -> bool:
    """Check if cache is still valid.

    Args:
        cache: Cache dictionary from load_cost_cache().
        cwd: Current working directory to check against cached cwd.

    Returns:
        True if cache is fresh and for the same directory, False otherwise.
    """
    if not cache:
        return False
    cache_time = cache.get("timestamp", 0)
    cache_cwd = cache.get("cwd", "")
    age = time.time() - cache_time
    return age < COST_CACHE_TTL_SECONDS and cache_cwd == cwd


def fetch_costs_raw(cwd: str) -> tuple[str, str, float, float]:
    """Fetch daily, session, and weekly costs from ccusage calls.

    Uses the `-i` flag which returns per-project breakdown that also includes
    daily totals, allowing both values to be extracted from one response.
    Also fetches weekly data for usage percentage calculation.

    Args:
        cwd: Current working directory, used to identify the project.

    Returns:
        Tuple of (daily_cost, session_cost, daily_cost_val, weekly_cost_val)
        where daily_cost/session_cost are formatted strings like "$X.XX"
        and daily_cost_val/weekly_cost_val are raw float values.
    """
    today = datetime.now().strftime("%Y%m%d")

    # Convert cwd to project name format (replace / with -)
    project_name = cwd.replace("/", "-").replace("\\", "-") if cwd else ""

    daily_cost_val = 0.0
    weekly_cost_val = 0.0

    # Try bunx (bun) first, then npx - single call with -i flag gets both values
    for cmd in [["bunx", "ccusage@latest"], ["npx", "ccusage@latest"]]:
        try:
            # Fetch today's costs
            result = subprocess.run(  # noqa: S603, S607
                [*cmd, "daily", "--json", "--since", today, "-i"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)

                # Extract daily total from the same response
                daily_cost_val = data.get("totals", {}).get("totalCost", 0)
                daily_cost = f"${daily_cost_val:.2f}"

                # Extract session/project cost
                session_cost = "$0.00"
                if project_name:
                    projects = data.get("projects", {})
                    if project_name in projects:
                        project_data = projects[project_name]
                        if project_data and len(project_data) > 0:
                            total_cost = sum(
                                entry.get("totalCost", 0) for entry in project_data
                            )
                            session_cost = f"${total_cost:.2f}"

                # Fetch weekly costs (last 7 days)
                week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y%m%d")
                weekly_result = subprocess.run(  # noqa: S603, S607
                    [*cmd, "daily", "--json", "--since", week_ago, "-i"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if weekly_result.returncode == 0 and weekly_result.stdout.strip():
                    weekly_data = json.loads(weekly_result.stdout)
                    weekly_cost_val = weekly_data.get("totals", {}).get("totalCost", 0)

                return daily_cost, session_cost, daily_cost_val, weekly_cost_val
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            continue

    return "$0.00", "$0.00", 0.0, 0.0


def _is_refresh_locked() -> bool:
    """Check if a background refresh is already running.

    Uses a lock file with a 60-second staleness check to prevent concurrent
    refreshes while not permanently blocking if a refresh process dies.

    Returns:
        True if a refresh is currently in progress, False otherwise.
    """
    try:
        if COST_REFRESH_LOCK.exists():
            lock_age = time.time() - COST_REFRESH_LOCK.stat().st_mtime
            # Consider lock stale after 60 seconds (refresh should finish in ~15s)
            if lock_age < 60:
                return True
            # Stale lock, remove it
            COST_REFRESH_LOCK.unlink(missing_ok=True)
    except OSError:
        pass
    return False


def spawn_background_refresh(cwd: str) -> None:
    """Spawn a background process to refresh the cost cache.

    Uses subprocess.Popen to run a small Python script that:
    1. Creates a lock file to prevent concurrent refreshes
    2. Runs the ccusage command
    3. Parses the result and writes to the cache file
    4. Removes the lock file

    Args:
        cwd: Current working directory for session cost lookup.
    """
    if _is_refresh_locked():
        debug_log("Background refresh already running, skipping")
        return

    debug_log("Spawning background refresh process")

    # Build the inline Python script for background execution
    refresh_script = f"""
import json, subprocess, time, sys
from pathlib import Path
from datetime import datetime, timedelta

lock_file = Path({str(COST_REFRESH_LOCK)!r})
cache_file = Path({str(COST_CACHE_FILE)!r})
cwd = {cwd!r}

try:
    # Create lock file
    lock_file.write_text(str(time.time()))

    today = datetime.now().strftime("%Y%m%d")
    week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y%m%d")
    project_name = cwd.replace("/", "-").replace("\\\\", "-") if cwd else ""

    daily_cost = "$0.00"
    session_cost = "$0.00"
    daily_cost_val = 0.0
    weekly_cost_val = 0.0

    for cmd in [["bunx", "ccusage@latest"], ["npx", "ccusage@latest"]]:
        try:
            result = subprocess.run(
                [*cmd, "daily", "--json", "--since", today, "-i"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                daily_cost_val = data.get("totals", {{}}).get("totalCost", 0)
                daily_cost = f"${{daily_cost_val:.2f}}"
                if project_name:
                    projects = data.get("projects", {{}})
                    if project_name in projects:
                        project_data = projects[project_name]
                        if project_data and len(project_data) > 0:
                            total_cost = sum(e.get("totalCost", 0) for e in project_data)
                            session_cost = f"${{total_cost:.2f}}"

                # Fetch weekly costs
                weekly_result = subprocess.run(
                    [*cmd, "daily", "--json", "--since", week_ago, "-i"],
                    capture_output=True, text=True, timeout=30,
                )
                if weekly_result.returncode == 0 and weekly_result.stdout.strip():
                    weekly_data = json.loads(weekly_result.stdout)
                    weekly_cost_val = weekly_data.get("totals", {{}}).get("totalCost", 0)

                break
        except Exception:
            continue

    cache = {{
        "daily_cost": daily_cost,
        "session_cost": session_cost,
        "daily_cost_val": daily_cost_val,
        "weekly_cost_val": weekly_cost_val,
        "timestamp": time.time(),
        "cwd": cwd,
    }}
    cache_file.write_text(json.dumps(cache))
finally:
    lock_file.unlink(missing_ok=True)
"""

    try:
        subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", refresh_script],  # noqa: S603
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        debug_log(f"Failed to spawn background refresh: {e}")


def get_costs_cached(cwd: str) -> tuple[str, str, float, float]:
    """Get daily and session costs with non-blocking cache refresh.

    Returns cached values immediately. If the cache is expired, returns stale
    values (or "$..." placeholders on first run) and spawns a background process
    to refresh the cache. This ensures the statusline always returns in <0.1s.

    Cache TTL is 300 seconds.

    Args:
        cwd: Current working directory for session cost lookup.

    Returns:
        Tuple of (daily_cost, session_cost, daily_cost_val, weekly_cost_val).
    """
    cache = load_cost_cache()

    if is_cache_valid(cache, cwd):
        debug_log(
            f"Using cached costs (age: {time.time() - cache.get('timestamp', 0):.1f}s)"
        )
        return (
            cache.get("daily_cost", "$0.00"),
            cache.get("session_cost", "$0.00"),
            cache.get("daily_cost_val", 0.0),
            cache.get("weekly_cost_val", 0.0),
        )

    # Cache is stale or missing - return immediately with stale/placeholder values
    if cache:
        stale_daily = cache.get("daily_cost", "$...")
        stale_session = cache.get("session_cost", "$...")
        stale_daily_val = cache.get("daily_cost_val", 0.0)
        stale_weekly_val = cache.get("weekly_cost_val", 0.0)
        debug_log(
            f"Cache expired, returning stale values: daily={stale_daily}, session={stale_session}"
        )
    else:
        stale_daily = "$..."
        stale_session = "$..."
        stale_daily_val = 0.0
        stale_weekly_val = 0.0
        debug_log("No cache exists, returning placeholders")

    # Spawn background refresh (fire and forget)
    spawn_background_refresh(cwd)

    return stale_daily, stale_session, stale_daily_val, stale_weekly_val


def get_claude_version() -> str:
    """Get the Claude Code version."""
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "--version"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Output is like "2.1.25 (Claude Code)"
            version = result.stdout.strip()
            # Extract just the version number (e.g., "2.1.25")
            version_num = version.split()[0] if version else "unknown"
            return f"v{version_num}"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "v?"


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
    effective_cwd = input_data.get("cwd") or os.getcwd()
    full_cwd = effective_cwd

    # Get daily and session costs (with caching for fast statusline refresh)
    daily_cost, session_cost, daily_cost_val, weekly_cost_val = get_costs_cached(
        full_cwd
    )

    # Get Claude version
    claude_version = get_claude_version()

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

    # Format costs: daily cost only
    daily_amount = daily_cost
    cost_display = f"{GREEN}\U0001f4b0 {daily_amount}{RESET}"

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
