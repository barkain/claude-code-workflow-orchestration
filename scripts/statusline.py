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
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Configuration
DEBUG_LOG = Path("/tmp/statusline_debug.log") if os.name != "nt" else Path(os.environ.get("TEMP", ".")) / "statusline_debug.log"


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
    project_dir = current_dir.replace(str(home), "~").replace("/", "-").replace("\\", "-").lstrip("-")
    project_file = home / ".claude" / "projects" / f"-{project_dir}" / f"{session_id}.jsonl"
    if project_file.exists():
        debug_log(f"Found session file (project): {project_file}")
        return project_file

    # Method 3: Project-based lookup (without tilde)
    alt_project_dir = current_dir.replace("/", "-").replace("\\", "-").lstrip("-")
    alt_project_file = home / ".claude" / "projects" / f"-{alt_project_dir}" / f"{session_id}.jsonl"
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
    current_dir = input_data.get("cwd") or input_data.get("workspace", {}).get("current_dir", "")

    debug_log(f"Session ID: {session_id}, Current Dir: {current_dir}")

    if not session_id:
        return None

    # Determine max context based on model
    model_name = input_data.get("model", {}).get("display_name") or input_data.get("model", {}).get("id", "")
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
                    token_entries.append({
                        "input": usage.get("input_tokens", 0),
                        "cache_read": usage.get("cache_read_input_tokens", 0),
                        "cache_create": usage.get("cache_creation_input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                    })
            except json.JSONDecodeError:
                continue

        debug_log(f"Token entries found: {len(token_entries)}")

        if token_entries:
            last_entry = token_entries[-1]
            total_input = last_entry["input"] + last_entry["cache_read"] + last_entry["cache_create"]

            debug_log(f"Last entry tokens - Input: {last_entry['input']}, Cache Read: {last_entry['cache_read']}, Cache Create: {last_entry['cache_create']}, Total: {total_input}")

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
        rel_path = full_path[len(home):].lstrip("/\\")
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
            ["git", "branch", "--show-current"],
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


def get_daily_cost() -> str:
    """Get today's cost from ccusage."""
    today = datetime.now().strftime("%Y%m%d")

    # Try bunx (bun) first, then npx
    for cmd in [["bunx", "ccusage@latest"], ["npx", "ccusage@latest"]]:
        try:
            result = subprocess.run(
                [*cmd, "daily", "--json", "--since", today],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                cost = data.get("totals", {}).get("totalCost", 0)
                return f"${cost:.2f} today"
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, OSError):
            continue

    return "$0.00 today"


def main() -> None:
    """Main entry point."""
    # Clear debug log at start
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write(f"=== Statusline run at {datetime.now()} ===\n")
    except OSError:
        pass

    # Color codes
    SHINY_AQUA = "\033[38;2;0;255;255m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

    # Read JSON input from stdin if available
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.loads(sys.stdin.read())
            # Save for debugging
            try:
                with open(Path("/tmp" if os.name != "nt" else os.environ.get("TEMP", ".")) / "statusline_input.json", "w") as f:
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

    # Get daily cost
    daily_cost = get_daily_cost()

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

    # Output statusline
    print(f"{SHINY_AQUA}🤖 {raw_model}{RESET} | {BLUE}🎨 {output_style}{RESET} | {GREEN}💰 {daily_cost}{RESET} | {context_info}")
    print(f"{YELLOW}{git_status}{RESET} | {WHITE}📁 {cwd}{RESET}")


if __name__ == "__main__":
    main()
