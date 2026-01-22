#!/usr/bin/env python3
"""
PostToolUse Hook: Python Code Validator (cross-platform)

Enhanced Universal Python Code Validator - validates Python files after Edit/Write/MultiEdit.
Blocks operations with CLAUDE.md violations + performance/security red flags.

This Python version works on Windows, macOS, and Linux.
"""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows (fixes emoji encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Debug mode
DEBUG_HOOK = os.environ.get("DEBUG_HOOK", "0") == "1"


def debug_log(message: str) -> None:
    """Write debug message if debugging is enabled."""
    if DEBUG_HOOK:
        print(f"[DEBUG] {message}", file=sys.stderr)


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)


def run_critical_security_check(content: str, file_path: str) -> list[str]:
    """Fast pattern matching for critical security issues."""
    violations = []

    # SQL Injection patterns
    if re.search(r"cursor\.execute\(.*%.*\)|\.execute\(.*\+.*\)", content):
        violations.append("Potential SQL injection vulnerability")

    # Command injection patterns
    if re.search(r"os\.system\(.*\+.*\)|subprocess\.(call|run)\(.*\+.*\)", content):
        violations.append("Potential command injection vulnerability")

    # Hardcoded secrets (more specific patterns)
    if re.search(r"(password|secret|token|api_key)\s*=\s*['\"][A-Za-z0-9]{16,}['\"]", content, re.IGNORECASE):
        violations.append("Hardcoded secret/credential detected")

    # Insecure random for security purposes
    if re.search(r"import random", content) and re.search(r"(password|token|secret|key)", content, re.IGNORECASE):
        violations.append("Using insecure random module for security purposes")

    # Dangerous eval/exec usage
    if re.search(r"\b(eval|exec)\s*\(", content):
        violations.append("Dangerous eval/exec usage detected")

    # Insecure SSL/TLS
    if re.search(r"ssl.*PROTOCOL_TLS|verify=False|check_hostname=False", content):
        violations.append("Insecure SSL/TLS configuration")

    return violations


def run_ruff_check(file_path: str) -> tuple[bool, list[str]]:
    """Run ruff check on the file."""
    # Try uvx ruff first, then ruff directly
    for cmd_prefix in [["uvx", "ruff"], ["ruff"]]:
        returncode, stdout, stderr = run_command(
            [*cmd_prefix, "check", "--select", "F,E711,E712,UP006,UP007,UP035,UP037,T201,S", file_path]
        )
        if returncode == 0:
            return True, []
        if "not found" not in stderr.lower():
            # Command exists but found issues
            issues = []
            for line in (stdout + stderr).split("\n"):
                if line.strip() and file_path in line:
                    issues.append(line.strip())
            return False, issues

    # Ruff not available
    debug_log("Ruff not available, skipping lint check")
    return True, []


def run_pyright_check(file_path: str) -> tuple[bool, list[str]]:
    """Run pyright type check on the file."""
    # Try uvx pyright first, then pyright directly
    for cmd_prefix in [["uvx", "pyright"], ["pyright"]]:
        returncode, stdout, stderr = run_command([*cmd_prefix, file_path])
        if returncode == 0:
            return True, []
        if "not found" not in stderr.lower():
            # Command exists but found issues
            issues = []
            for line in (stdout + stderr).split("\n"):
                if "error:" in line.lower():
                    issues.append(line.strip())
            return len(issues) == 0, issues[:5]  # Limit to 5 issues

    # Pyright not available
    debug_log("Pyright not available, skipping type check")
    return True, []


def validate_python_content(content: str, file_path: str) -> tuple[bool, list[str]]:
    """Validate Python content and return (passed, errors)."""
    errors = []

    # 1. Critical security check (fastest, always run)
    security_issues = run_critical_security_check(content, file_path)
    if security_issues:
        errors.extend([f"CRITICAL SECURITY: {issue}" for issue in security_issues])

    # 2. Create temp file for tool-based validation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_file = f.name

    try:
        # 3. Ruff check
        passed, ruff_errors = run_ruff_check(temp_file)
        if not passed:
            errors.extend([f"Lint: {e}" for e in ruff_errors[:5]])

        # 4. Pyright check
        passed, pyright_errors = run_pyright_check(temp_file)
        if not passed:
            errors.extend([f"Type: {e}" for e in pyright_errors])
    finally:
        try:
            Path(temp_file).unlink()
        except OSError:
            pass

    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    # Read hook input from stdin
    try:
        json_input = sys.stdin.read()
        data = json.loads(json_input) if json_input else {}
    except json.JSONDecodeError:
        debug_log("Invalid JSON input")
        return 0

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only handle Edit/Write/MultiEdit tools
    if tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("new_string", "")
    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
    elif tool_name == "MultiEdit":
        file_path = tool_input.get("file_path", "")
        edits = tool_input.get("edits", [])
        content = "\n".join(edit.get("new_string", "") for edit in edits)
    else:
        debug_log(f"Unknown tool '{tool_name}', allowing silently")
        return 0

    # Only validate Python files
    if not file_path.endswith(".py"):
        return 0

    # For Edit, we need the full file content, not just the new_string
    # Try to read the actual file if it exists
    if tool_name == "Edit" and Path(file_path).exists():
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except OSError:
            pass

    # Validate the content
    passed, errors = validate_python_content(content, file_path)

    if not passed:
        print("", file=sys.stderr)
        print("🚫 CRITICAL VIOLATIONS DETECTED", file=sys.stderr)
        print("", file=sys.stderr)
        print("Specific violations found:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        print("", file=sys.stderr)
        print("⚠️  CLAUDE.md standards and/or security violations found", file=sys.stderr)
        print("🔒 Critical security issues MUST be fixed before proceeding", file=sys.stderr)
        print("📋 Fix all violations and retry the operation", file=sys.stderr)
        return 2  # Block the operation

    print("✅ All critical validations passed")
    print("", file=sys.stderr)
    print("📝 REMINDER: Update the todo list", file=sys.stderr)
    print("", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
