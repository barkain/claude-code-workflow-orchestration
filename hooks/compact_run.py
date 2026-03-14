#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
compact_run.py — Lightweight output compressor for Claude Code (cross-platform)

Runs a command, captures output, and applies compression:
  - Git ops:    success -> one-liner summary, failure -> full stderr
  - Log cmds:   dedup repeated lines + tail
  - Test cmds:  success -> summary line, failure -> failures only

Install: Part of workflow-orchestrator plugin (hooks/compact_run.py)
Called by token_rewrite_hook.py, never directly by Claude.
"""

import io
import os
import re
import subprocess
import sys

# Force UTF-8 output on Windows (fixes encoding errors)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- Config ---
MAX_LINES = 150  # Truncation safety net
LOG_TAIL = 50  # Max log lines to show
LOG_DEDUP = True  # Deduplicate log lines
CMD_TIMEOUT = int(
    os.environ.get("COMPACT_RUN_TIMEOUT", "120")
)  # Max seconds (env-configurable)


def truncated_output(content: str) -> str:
    """Apply truncation safety net."""
    lines = content.splitlines()
    total = len(lines)
    if total > MAX_LINES:
        truncated = lines[-MAX_LINES:]
        return (
            f"[truncated: {total} lines total, showing last {MAX_LINES}]\n"
            + "\n".join(truncated)
        )
    return content


def emit_failure(stdout: str, stderr: str, exit_code: int) -> int:
    """On failure, show stderr + truncated stdout, then exit."""
    if stderr:
        print(stderr, file=sys.stderr)  # noqa: T201
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    return exit_code


def handle_git(args: list[str], stdout: str, stderr: str, exit_code: int) -> int:
    """Handle git command compression."""
    if exit_code != 0:
        return emit_failure(stdout, stderr, exit_code)

    second = args[1] if len(args) > 1 else ""
    combined = stdout + stderr

    if second == "push":
        # Extract branch from "-> branch" pattern
        match = re.search(r"-> (\S+)", combined)
        if match:
            branch = match.group(1)
        else:
            result = subprocess.run(  # noqa: S603
                ["git", "branch", "--show-current"],  # noqa: S607
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip() if result.returncode == 0 else "?"
        print(f"ok \u2192 {branch}")  # noqa: T201

    elif second == "pull":
        match = re.search(r"\s*(\d+ files? changed.*)", stdout)
        if match:
            print(f"ok \u2192 {match.group(1).strip()}")  # noqa: T201
        elif "Already up to date" in stdout:
            print("ok \u2192 already up to date")  # noqa: T201
        else:
            print("ok")  # noqa: T201

    elif second == "commit":
        match = re.search(r"\[.+ ([a-f0-9]{7,})\] (.+)", combined)
        if match:
            hash_val = match.group(1)
            msg = match.group(2)
            print(f'ok \u2192 {hash_val} "{msg}"')  # noqa: T201
        else:
            print("ok")  # noqa: T201

    elif second == "add":
        print("ok")  # noqa: T201

    elif second == "fetch":
        new_refs = len(re.findall(r"^\s*(From|\[new|->)", combined, re.MULTILINE))
        if new_refs > 0:
            print(f"ok \u2192 {new_refs} new refs")  # noqa: T201
        else:
            print("ok")  # noqa: T201

    elif second == "merge":
        if "Already up to date" in stdout:
            print("ok \u2192 already up to date")  # noqa: T201
        else:
            match = re.search(r"\s*(\d+ files? changed.*)", stdout)
            summary = match.group(1).strip() if match else "merged"
            print(f"ok \u2192 {summary}")  # noqa: T201

    elif second == "rebase":
        match = re.search(r"Successfully rebased.*", combined)
        summary = match.group(0) if match else "rebased"
        print(f"ok \u2192 {summary}")  # noqa: T201

    elif second == "stash":
        if re.search(r"saved working directory", stdout, re.IGNORECASE):
            print("ok \u2192 stashed")  # noqa: T201
        elif re.search(r"dropped", stdout, re.IGNORECASE):
            print("ok \u2192 dropped")  # noqa: T201
        elif re.search(r"no local changes", stdout, re.IGNORECASE):
            print("ok \u2192 nothing to stash")  # noqa: T201
        else:
            # stash list, stash show, etc. — pass through
            print(truncated_output(stdout))  # noqa: T201

    else:
        print(truncated_output(stdout))  # noqa: T201

    return exit_code


def handle_container_logs(stdout: str, stderr: str, exit_code: int) -> int:
    """Handle docker/podman/kubectl logs compression."""
    if exit_code != 0:
        return emit_failure(stdout, stderr, exit_code)

    if LOG_DEDUP:
        # Deduplicate consecutive identical lines
        lines = stdout.splitlines()
        deduped: list[str] = []
        prev = None
        count = 0
        for line in lines:
            if line == prev:
                count += 1
            else:
                if count > 1:
                    deduped.append(f"  [repeated {count} times]")
                if prev is not None or line != "":
                    deduped.append(line)
                prev = line
                count = 1
        if count > 1:
            deduped.append(f"  [repeated {count} times]")

        total = len(deduped)
        if total > LOG_TAIL:
            print(f"[showing last {LOG_TAIL} of {total} lines, duplicates collapsed]")  # noqa: T201
            print("\n".join(deduped[-LOG_TAIL:]))  # noqa: T201
        else:
            print("\n".join(deduped))  # noqa: T201
    else:
        lines = stdout.splitlines()
        print("\n".join(lines[-LOG_TAIL:]))  # noqa: T201

    return exit_code


def handle_pytest(stdout: str, stderr: str, exit_code: int) -> int:
    """Handle pytest output compression."""
    if exit_code == 0:
        match = re.search(r"(\d+ passed in [0-9.]+s)", stdout)
        summary = match.group(1) if match else "all passed"
        print(f"ok \u2192 {summary}")  # noqa: T201
        return exit_code

    # Show FAILURES section if present, otherwise full failure output
    failures_match = re.search(
        r"(^=+ FAILURES.*?^=+ short test summary)",
        stdout,
        re.MULTILINE | re.DOTALL,
    )
    if failures_match:
        failures = failures_match.group(0)
        print(truncated_output(failures))  # noqa: T201
        # Also grab FAILED/ERROR summary lines
        summary_lines = re.findall(r"^(?:FAILED|ERROR).*", stdout, re.MULTILINE)
        for line in summary_lines[-5:]:
            print(line)  # noqa: T201
    else:
        emit_failure(stdout, stderr, exit_code)
        return exit_code

    if stderr:
        print(stderr, file=sys.stderr)  # noqa: T201
    return exit_code


def handle_cargo(args: list[str], stdout: str, stderr: str, exit_code: int) -> int:
    """Handle cargo command compression."""
    second = args[1] if len(args) > 1 else ""

    if second == "test":
        if exit_code == 0:
            match = re.search(r"test result: ok\. \d+ passed; \d+ failed", stdout)
            summary = match.group(0) if match else "all passed"
            print(f"ok \u2192 {summary}")  # noqa: T201
        else:
            failures = re.findall(
                r"(^test .+ FAILED|^---- .+ ---|^thread.*panicked|failures:).*",
                stdout,
                re.MULTILINE,
            )
            if failures:
                for line in failures:
                    print(line)  # noqa: T201
                match = re.search(r"test result: FAILED\. \d+ passed.*", stdout)
                if match:
                    print(match.group(0))  # noqa: T201
            else:
                emit_failure(stdout, stderr, exit_code)
                return exit_code
            if stderr:
                print(stderr, file=sys.stderr)  # noqa: T201
        return exit_code

    # cargo build, cargo clippy, etc. — pass through with truncation
    if stderr:
        print(truncated_output(stderr), file=sys.stderr)  # noqa: T201
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    return exit_code


def handle_node_test(stdout: str, stderr: str, exit_code: int) -> int:
    """Handle npm/pnpm/yarn/bun test compression."""
    if exit_code == 0:
        match = re.search(
            r"(Tests?:?\s+\d+ passed|\d+ passing|test suites?:.*passed|\d+ tests? passed)",
            stdout,
            re.IGNORECASE,
        )
        summary = match.group(0) if match else "all passed"
        print(f"ok \u2192 {summary}")  # noqa: T201
        return exit_code

    return emit_failure(stdout, stderr, exit_code)


def handle_npx(args: list[str], stdout: str, stderr: str, exit_code: int) -> int:
    """Handle npx command compression."""
    second = args[1] if len(args) > 1 else ""

    if second in ("vitest", "jest", "mocha", "playwright"):
        if exit_code == 0:
            match = re.search(
                r"(Tests?:?\s+\d+ passed|\d+ passing|test suites?:.*passed|\d+ tests? passed)",
                stdout,
                re.IGNORECASE,
            )
            summary = match.group(0) if match else "all passed"
            print(f"ok \u2192 {summary}")  # noqa: T201
            return exit_code
        return emit_failure(stdout, stderr, exit_code)

    # Other npx commands — pass through
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    if stderr:
        print(truncated_output(stderr), file=sys.stderr)  # noqa: T201
    return exit_code


def handle_go(args: list[str], stdout: str, stderr: str, exit_code: int) -> int:
    """Handle go command compression."""
    second = args[1] if len(args) > 1 else ""

    if second == "test":
        if exit_code == 0:
            pkg_count = len(re.findall(r"^ok\s+.*", stdout, re.MULTILINE))
            print(f"ok \u2192 {pkg_count} packages passed")  # noqa: T201
        else:
            failures = re.findall(
                r"(^--- FAIL.*|^FAIL\s.*|panic:.*)", stdout, re.MULTILINE
            )
            if failures:
                for line in failures:
                    print(line)  # noqa: T201
            else:
                emit_failure(stdout, stderr, exit_code)
                return exit_code
            if stderr:
                print(stderr, file=sys.stderr)  # noqa: T201
        return exit_code

    # Other go commands — pass through
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    if stderr:
        print(truncated_output(stderr), file=sys.stderr)  # noqa: T201
    return exit_code


def handle_make(args: list[str], stdout: str, stderr: str, exit_code: int) -> int:
    """Handle make command compression."""
    second = args[1] if len(args) > 1 else ""

    if second in ("test", "check"):
        if exit_code == 0:
            print("ok")  # noqa: T201
            return exit_code
        return emit_failure(stdout, stderr, exit_code)

    # Other make targets — pass through
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    if stderr:
        print(truncated_output(stderr), file=sys.stderr)  # noqa: T201
    return exit_code


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: compact_run.py <command> [args...]", file=sys.stderr)  # noqa: T201
        return 1

    args = sys.argv[1:]

    # --- Run the actual command ---
    # Use shell=False for safety; pass args list directly
    # On Windows, some commands may need shell=True, but for the supported
    # command families (git, docker, pytest, etc.) shell=False works.
    try:
        result = subprocess.run(  # noqa: S603
            args,
            capture_output=True,
            text=True,
            timeout=CMD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print(
            f"command timed out after {CMD_TIMEOUT}s: {' '.join(args)}", file=sys.stderr
        )  # noqa: T201
        return 1
    except FileNotFoundError:
        print(f"command not found: {args[0]}", file=sys.stderr)  # noqa: T201
        return 1
    except OSError as e:
        print(f"error running command: {e}", file=sys.stderr)  # noqa: T201
        return 1

    stdout = result.stdout
    stderr = result.stderr
    exit_code = result.returncode

    first = args[0]
    # Strip path and .exe suffix for cross-platform matching (e.g., /usr/bin/git -> git, git.exe -> git)
    first_base = os.path.basename(first)
    name, ext = os.path.splitext(first_base)
    if ext.lower() == ".exe":
        first_base = name

    # --- Route by command type ---

    if first_base == "git":
        return handle_git(args, stdout, stderr, exit_code)

    if first_base in ("docker", "podman", "kubectl"):
        second = args[1] if len(args) > 1 else ""
        if second == "logs":
            return handle_container_logs(stdout, stderr, exit_code)
        if exit_code != 0:
            return emit_failure(stdout, stderr, exit_code)
        print(truncated_output(stdout))  # noqa: T201
        return exit_code

    if first_base in ("pytest", "py.test"):
        return handle_pytest(stdout, stderr, exit_code)

    if first_base == "cargo":
        return handle_cargo(args, stdout, stderr, exit_code)

    if first_base in ("npm", "pnpm", "yarn", "bun"):
        second = args[1] if len(args) > 1 else ""
        if second == "test":
            return handle_node_test(stdout, stderr, exit_code)
        if stdout:
            print(truncated_output(stdout))  # noqa: T201
        if stderr:
            print(truncated_output(stderr), file=sys.stderr)  # noqa: T201
        return exit_code

    if first_base == "npx":
        return handle_npx(args, stdout, stderr, exit_code)

    if first_base == "go":
        return handle_go(args, stdout, stderr, exit_code)

    if first_base == "make":
        return handle_make(args, stdout, stderr, exit_code)

    # --- Fallback — truncation safety net only ---
    if stderr:
        print(stderr, file=sys.stderr)  # noqa: T201
    if stdout:
        print(truncated_output(stdout))  # noqa: T201
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
