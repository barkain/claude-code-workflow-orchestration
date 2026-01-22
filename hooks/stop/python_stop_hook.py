#!/usr/bin/env python3
"""
Stop Hook: Workflow Continuation + Code Quality Analysis (cross-platform)

1. Checks if workflow continuation is needed (after task-planner completes)
   - If so, blocks stop and injects "continue" as user message
2. Runs code quality checks on staged Python files (informational only)

This Python version works on Windows, macOS, and Linux.
"""

import io
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Setup debug logging
DEBUG = os.environ.get("DEBUG_DELEGATION_HOOK", "0") == "1"
if DEBUG:
    logging.basicConfig(
        filename="/tmp/delegation_hook_debug.log",
        level=logging.DEBUG,
        format="%(asctime)s - python_stop_hook - %(message)s",
    )
else:
    logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)


def check_workflow_continuation() -> bool:
    """Check if workflow continuation is needed and handle it.

    Returns True if stop should be blocked (continuation needed).
    Returns False to allow normal stop processing.
    """
    state_file = Path(".claude/state/workflow_continuation_needed.json")

    if not state_file.exists():
        logger.debug("No continuation state file found")
        return False

    logger.debug(f"Found continuation state file: {state_file}")

    try:
        # Read and remove state file
        state_data = json.loads(state_file.read_text())
        state_file.unlink()
        logger.debug(f"State data: {state_data}, file removed")

        # Output block decision to prevent stop and inject "continue"
        # This mimics ralph-wiggum's loop mechanism
        output = {
            "decision": "block",
            "reason": "continue",
            "systemMessage": "⚡ Workflow continuation: Proceeding to STAGE 1 execution."
        }
        print(json.dumps(output))
        logger.debug("Output block decision with 'continue' reason")
        return True

    except (json.JSONDecodeError, OSError) as e:
        logger.debug(f"Error processing state file: {e}")
        # Clean up corrupted file
        try:
            state_file.unlink()
        except OSError:
            pass
        return False


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)


def is_git_repo() -> bool:
    """Check if we're in a git repository."""
    returncode, _, _ = run_command(["git", "rev-parse", "--git-dir"])
    return returncode == 0


def get_staged_python_files() -> list[str]:
    """Get staged Python files that are not deleted."""
    returncode, stdout, _ = run_command(["git", "diff", "--cached", "--name-status"])
    if returncode != 0:
        return []

    files = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status, file_path = parts[0], parts[-1]
            if status in ("A", "M") and file_path.endswith(".py"):
                if Path(file_path).exists():
                    files.append(file_path)
    return files


def run_validation_check(files: list[str]) -> tuple[bool, list[str]]:
    """Run ruff validation on files."""
    issues = []
    for file in files:
        for cmd_prefix in [["uvx", "ruff"], ["ruff"]]:
            returncode, stdout, stderr = run_command([*cmd_prefix, "check", file])
            if "not found" not in stderr.lower():
                if returncode != 0:
                    issues.append(f"{file}: validation issues found")
                break
    return len(issues) == 0, issues


def run_security_check(files: list[str]) -> tuple[bool, list[str]]:
    """Basic security pattern check on files."""
    import re

    issues = []
    patterns = [
        (r"(password|secret|token|key|api_key)\s*=\s*['\"][^'\"]{8,}", "Potential hardcoded credentials"),
        (r"cursor\.execute\(.*%.*\)", "Potential SQL injection"),
        (r"(os\.system|subprocess\.call).*\+.*", "Potential command injection"),
    ]

    for file in files:
        try:
            content = Path(file).read_text(encoding="utf-8")
            for pattern, message in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"{file}: {message}")
        except OSError:
            pass

    return len(issues) == 0, issues


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'━' * 50}")
    print(f"  {title}")
    print(f"{'━' * 50}\n")


def main() -> int:
    """Main entry point."""
    # Check if workflow continuation is needed first
    # If so, block stop and inject "continue" - skip quality analysis
    if check_workflow_continuation():
        return 0

    print_header("🚀 Claude Code Enhanced Quality Analysis")
    print("Comprehensive quality checks on staged Python files...")

    # Check if we're in a git repository
    if not is_git_repo():
        print("⚠️  Not in a git repository - skipping checks")
        return 0

    # Get staged Python files
    staged_files = get_staged_python_files()

    if not staged_files:
        print("ℹ️  No staged Python files to analyze")
        return 0

    print(f"ℹ️  Found {len(staged_files)} staged Python file(s):")
    for file in staged_files:
        print(f"  • {file}")
    print()

    # Track results
    results = {}

    # Run checks
    print_header("🔍 Code Validation")
    passed, issues = run_validation_check(staged_files)
    results["validation"] = passed
    if passed:
        print("✅ Code validation passed")
    else:
        print("⚠️  Validation issues found:")
        for issue in issues[:5]:
            print(f"  {issue}")

    print_header("🔒 Security Analysis")
    passed, issues = run_security_check(staged_files)
    results["security"] = passed
    if passed:
        print("✅ No security issues detected")
    else:
        print("⚠️  Security issues found:")
        for issue in issues[:5]:
            print(f"  {issue}")

    # Summary
    print_header("📋 Quality Report")
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    score = (passed_count * 100) // total_count if total_count > 0 else 100

    for check, passed in results.items():
        status = "✅ PASSED" if passed else "⚠️  ISSUES"
        print(f"  {check.title()}: {status}")

    print(f"\n  Quality Score: {score}% ({passed_count}/{total_count} checks passed)")

    # Generate report file
    report_file = Path(f"/tmp/claude_quality_report_{datetime.now():%Y%m%d_%H%M%S}.md")
    try:
        report_content = f"""# Claude Code Quality Report
Date: {datetime.now():%Y-%m-%d %H:%M:%S}
Files analyzed: {len(staged_files)}
Quality Score: {score}%

## Checks
"""
        for check, passed in results.items():
            status = "PASSED" if passed else "ISSUES"
            report_content += f"- {check.title()}: {status}\n"

        report_file.write_text(report_content, encoding="utf-8")
        print(f"\n  Full report saved to: {report_file}")
    except OSError:
        pass

    # Always exit 0 for stop hooks (informational only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
