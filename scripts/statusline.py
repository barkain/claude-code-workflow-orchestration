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
from datetime import datetime
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

    # Calculate filled blocks (20 total)
    filled_blocks = percentage * 20 // 100
    empty_blocks = 20 - filled_blocks

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


def calculate_context_usage(input_data: dict) -> str | None:
    """Calculate actual context usage from session file."""
    session_id = input_data.get("session_id", "")
    current_dir = input_data.get("cwd") or input_data.get("workspace", {}).get(
        "current_dir", ""
    )

    debug_log(f"Session ID: {session_id}, Current Dir: {current_dir}")

    if not session_id:
        return None

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
        return None

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
                return f"🧠 {progress_bar}"

    except OSError as e:
        debug_log(f"Error reading session file: {e}")

    return None


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


def get_git_branch() -> str:
    """Get the current git branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],  # noqa: S607, S603
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            branch = result.stdout.strip()
            if len(branch) > 60:
                branch = branch[:60] + "..."
            return f"🌿 {branch} ⚡"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "🌿 no-git"


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


def save_cost_cache(daily_cost: str, session_cost: str, cwd: str) -> None:
    """Save cost values to cache file.

    Args:
        daily_cost: Formatted daily cost string.
        session_cost: Formatted session cost string.
        cwd: Current working directory (for cache invalidation).
    """
    cache = {
        "daily_cost": daily_cost,
        "session_cost": session_cost,
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


def fetch_costs_raw(cwd: str) -> tuple[str, str]:
    """Fetch daily and session costs from a single ccusage call.

    Uses the `-i` flag which returns per-project breakdown that also includes
    daily totals, allowing both values to be extracted from one response.

    Args:
        cwd: Current working directory, used to identify the project.

    Returns:
        Tuple of (daily_cost, session_cost) formatted strings like "$X.XX".
    """
    today = datetime.now().strftime("%Y%m%d")

    # Convert cwd to project name format (replace / with -)
    project_name = cwd.replace("/", "-").replace("\\", "-") if cwd else ""

    # Try bunx (bun) first, then npx - single call with -i flag gets both values
    for cmd in [["bunx", "ccusage@latest"], ["npx", "ccusage@latest"]]:
        try:
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

                return daily_cost, session_cost
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            continue

    return "$0.00", "$0.00"


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
from datetime import datetime

lock_file = Path({str(COST_REFRESH_LOCK)!r})
cache_file = Path({str(COST_CACHE_FILE)!r})
cwd = {cwd!r}

try:
    # Create lock file
    lock_file.write_text(str(time.time()))

    today = datetime.now().strftime("%Y%m%d")
    project_name = cwd.replace("/", "-").replace("\\\\", "-") if cwd else ""

    daily_cost = "$0.00"
    session_cost = "$0.00"

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
                break
        except Exception:
            continue

    cache = {{
        "daily_cost": daily_cost,
        "session_cost": session_cost,
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


def get_costs_cached(cwd: str) -> tuple[str, str]:
    """Get daily and session costs with non-blocking cache refresh.

    Returns cached values immediately. If the cache is expired, returns stale
    values (or "$..." placeholders on first run) and spawns a background process
    to refresh the cache. This ensures the statusline always returns in <0.1s.

    Cache TTL is 300 seconds.

    Args:
        cwd: Current working directory for session cost lookup.

    Returns:
        Tuple of (daily_cost, session_cost) formatted strings like "$X.XX".
    """
    cache = load_cost_cache()

    if is_cache_valid(cache, cwd):
        debug_log(
            f"Using cached costs (age: {time.time() - cache.get('timestamp', 0):.1f}s)"
        )
        return cache.get("daily_cost", "$0.00"), cache.get("session_cost", "$0.00")

    # Cache is stale or missing - return immediately with stale/placeholder values
    if cache:
        stale_daily = cache.get("daily_cost", "$...")
        stale_session = cache.get("session_cost", "$...")
        debug_log(
            f"Cache expired, returning stale values: daily={stale_daily}, session={stale_session}"
        )
    else:
        stale_daily = "$..."
        stale_session = "$..."
        debug_log("No cache exists, returning placeholders")

    # Spawn background refresh (fire and forget)
    spawn_background_refresh(cwd)

    return stale_daily, stale_session


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


def generate_sparkline(durations: list[float]) -> str:
    """Generate a sparkline visualization from duration values.

    Maps each duration to a block character based on its relative position
    between the min and max values in the array.

    Args:
        durations: List of duration values in seconds.

    Returns:
        Sparkline string using block characters (e.g., "▁▃▅▂█").
    """
    if not durations:
        return ""

    # Sparkline characters from lowest to highest
    spark_chars = "▁▂▃▄▅▆▇█"
    max_index = len(spark_chars) - 1

    min_val = min(durations)
    max_val = max(durations)
    value_range = max_val - min_val

    sparkline = ""
    for duration in durations:
        if value_range == 0:
            # All values are equal - use middle height
            index = max_index // 2
        else:
            # Map value to 0-7 index based on position in range
            normalized = (duration - min_val) / value_range
            index = int(normalized * max_index)
            # Clamp to valid range
            index = max(0, min(max_index, index))
        sparkline += spark_chars[index]

    return sparkline


def get_duration_history() -> list[float]:
    """Get the history of turn durations for sparkline visualization.

    Reads from the JSON file maintained by the stop hook.

    Returns:
        List of duration values in seconds, or empty list if not available.
    """
    state_dir = (
        Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())) / ".claude" / "state"
    )
    history_file = state_dir / "turn_durations.json"

    if not history_file.exists():
        return []

    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        durations = data.get("durations", [])
        # Validate and convert to floats
        return [float(d) for d in durations if isinstance(d, int | float)]
    except (json.JSONDecodeError, ValueError, OSError):
        return []


def get_turn_duration() -> str | None:
    """Get the duration of the last completed turn with sparkline visualization.

    Reads from the state file written by the stop hook which calculates
    duration from UserPromptSubmit to Stop events. Also includes a sparkline
    showing the trend of the last 10 turn durations.

    Returns:
        Formatted duration string like "▁▃▅▂█ 45s", or None if not available.
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
            # Get sparkline from duration history
            durations = get_duration_history()
            sparkline = generate_sparkline(durations)

            if sparkline:
                # Color the sparkline with coral/salmon (RGB true color)
                # Fallback-safe: Windows Terminal supports RGB, older terminals ignore
                CORAL = "\033[38;2;255;127;80m"
                RESET = "\033[0m"
                return f"{CORAL}{sparkline}{RESET} {duration_str}"
            return duration_str
    except OSError:
        pass

    return None


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
    output_style = input_data.get("output_style", {}).get("name", "default")

    debug_log(f"Model: {raw_model}, Style: {output_style}")

    # Get current working directory for project-based cost tracking
    full_cwd = os.getcwd()

    # Get daily and session costs (with caching for fast statusline refresh)
    daily_cost, session_cost = get_costs_cached(full_cwd)

    # Get Claude version
    claude_version = get_claude_version()

    # Get context info
    context_info = calculate_context_usage(input_data)
    if not context_info:
        # Fallback empty progress bar
        max_context = 200000
        if "1M" in raw_model:
            max_context = 1_000_000
        progress_bar = create_progress_bar(0, 0, max_context)
        context_info = f"🧠 {progress_bar}"

    # Get git status
    git_status = get_git_branch()

    # Get shortened CWD
    cwd = shorten_cwd(os.getcwd())

    # Get turn duration if available
    turn_duration = get_turn_duration()

    # Format costs: extract numbers and combine as "💰 $Y.YY (🎯 $X.XX)"
    # where daily_cost is first (larger), session_cost in parentheses
    # session_cost format: "$X.XX"
    # daily_cost format: "$Y.YY"
    daily_amount = daily_cost
    session_amount = session_cost
    cost_display = f"{GREEN}💰 {daily_amount} (🎯 {session_amount}){RESET}"

    # Output statusline (print is required for statusline output)
    # Row 1: Claude version first, then model, style, costs, context
    sys.stdout.write(
        f"{BLUE}{claude_version}{RESET} | {SHINY_AQUA}🤖 {raw_model}{RESET} | {BLUE}🎨 {output_style}{RESET} | {cost_display} | {context_info}\n"
    )
    # Row 2: Turn duration, git branch, CWD (cyan for visibility on both light/dark themes)
    cwd_display = f"{SHINY_AQUA}📁 {cwd}{RESET}"
    if turn_duration:
        turn_display = f"{YELLOW}⏱️ {turn_duration}{RESET} | "
        sys.stdout.write(f"{turn_display}{YELLOW}{git_status}{RESET} | {cwd_display}\n")
    else:
        sys.stdout.write(f"{YELLOW}{git_status}{RESET} | {cwd_display}\n")


if __name__ == "__main__":
    main()
