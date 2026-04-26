"""Tests for hooks/PreToolUse/require_delegation.py (soft adaptive nudges)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK = PROJECT_ROOT / "hooks" / "PreToolUse" / "require_delegation.py"
_UV = shutil.which("uv") or "uv"


def _run(
    stdin: str,
    project_dir: Path,
    env_extra: dict[str, str] | None = None,
) -> tuple[str, str, int]:
    """Run the hook in an isolated project dir, return (stdout, stderr, rc)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    # Strip subagent markers so we test main-agent behavior unless overridden
    env.pop("CLAUDE_PARENT_SESSION_ID", None)
    env.pop("CLAUDE_AGENT_ID", None)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(  # noqa: S603
        [_UV, "run", "--no-project", "--script", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
        timeout=10,
    )
    return result.stdout, result.stderr, result.returncode


def _input(tool_name: str) -> str:
    return json.dumps({"tool_name": tool_name, "tool_input": {}})


# ---------------------------------------------------------------------------
# Always returns 0
# ---------------------------------------------------------------------------


class TestNeverBlocks:
    def test_work_tool_returns_zero(self, tmp_path: Path) -> None:
        _, _, rc = _run(_input("Bash"), tmp_path)
        assert rc == 0  # noqa: S101

    def test_unknown_tool_returns_zero(self, tmp_path: Path) -> None:
        _, _, rc = _run(_input("FooBarBaz"), tmp_path)
        assert rc == 0  # noqa: S101

    def test_empty_stdin_returns_zero(self, tmp_path: Path) -> None:
        _, _, rc = _run("", tmp_path)
        assert rc == 0  # noqa: S101

    def test_malformed_stdin_returns_zero(self, tmp_path: Path) -> None:
        _, _, rc = _run("not json", tmp_path)
        assert rc == 0  # noqa: S101


# ---------------------------------------------------------------------------
# Stable violation set: only WORK_TOOLS trigger nudges
# ---------------------------------------------------------------------------


class TestViolationSet:
    @pytest.mark.parametrize(
        "tool",
        ["Bash", "Edit", "Write", "Glob", "Grep", "MultiEdit", "NotebookEdit"],
    )
    def test_work_tools_count_as_violations(self, tmp_path: Path, tool: str) -> None:
        _, stderr, _ = _run(_input(tool), tmp_path)
        assert "delegate" in stderr.lower()  # noqa: S101

    def test_read_is_silent(self, tmp_path: Path) -> None:
        """Read is exempt from delegation nudges (not in WORK_TOOLS)."""
        _, stderr, rc = _run(_input("Read"), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101
        # Counter file should not be created/incremented for Read
        counter_file = tmp_path / ".claude" / "state" / "delegation_violations.json"
        if counter_file.exists():
            counter = json.loads(counter_file.read_text())
            assert counter["violations"] == 0  # noqa: S101

    @pytest.mark.parametrize(
        "tool",
        [
            "AskUserQuestion",
            "TaskCreate",
            "TaskUpdate",
            "Agent",
            "Task",
            "Skill",
            "SlashCommand",
            "EnterPlanMode",
            "ExitPlanMode",
            "ToolSearch",
            "TeamCreate",
            "SendMessage",
            "FooBar",  # hypothetical new tool
            "CronCreate",
        ],
    )
    def test_non_work_tools_silent(self, tmp_path: Path, tool: str) -> None:
        _, stderr, rc = _run(_input(tool), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101


# ---------------------------------------------------------------------------
# Escalation ladder
# ---------------------------------------------------------------------------


class TestEscalationLadder:
    def test_first_violation_is_imperative(self, tmp_path: Path) -> None:
        _, stderr, _ = _run(_input("Bash"), tmp_path)
        # New imperative message must include STOP + the delegate command
        assert "STOP" in stderr  # noqa: S101
        assert "/workflow-orchestrator:delegate" in stderr  # noqa: S101

    def test_second_violation_is_medium(self, tmp_path: Path) -> None:
        _run(_input("Bash"), tmp_path)
        _, stderr, _ = _run(_input("Edit"), tmp_path)
        assert "STOP" in stderr  # noqa: S101
        assert "/workflow-orchestrator:delegate" in stderr  # noqa: S101
        # Distinct 2nd-call phrasing
        assert "2nd direct tool call" in stderr  # noqa: S101

    def test_third_violation_is_warning(self, tmp_path: Path) -> None:
        for tool in ("Bash", "Edit", "Write"):
            _run(_input(tool), tmp_path)
        _, stderr, _ = _run(_input("Glob"), tmp_path)
        # 4th call -> "STOP. 4 direct tool calls bypassing delegation..."
        assert "STOP" in stderr  # noqa: S101
        assert "4" in stderr  # noqa: S101
        assert "/workflow-orchestrator:delegate" in stderr  # noqa: S101

    def test_fifth_plus_is_strong(self, tmp_path: Path) -> None:
        for _ in range(5):
            _run(_input("Bash"), tmp_path)
        _, stderr, _ = _run(_input("Bash"), tmp_path)  # 6th call
        assert "STOP" in stderr  # noqa: S101
        # The ≥3 message explains what's being lost
        assert "losing planning, parallelization, and context isolation" in stderr  # noqa: S101
        # Long message — over ~100 chars
        assert len(stderr.strip()) > 100  # noqa: S101

    def test_message_length_grows(self, tmp_path: Path) -> None:
        """Verify escalation adds context (proxied by message length/content)."""
        lengths = []
        messages = []
        for _ in range(6):
            _, stderr, _ = _run(_input("Bash"), tmp_path)
            lengths.append(len(stderr.strip()))
            messages.append(stderr.strip())
        # Each level should be at least as long as the previous (monotonic)
        for i in range(1, len(lengths)):
            assert lengths[i] >= lengths[i - 1]  # noqa: S101
        # The final message should be strictly longer than the first
        assert lengths[-1] > lengths[0]  # noqa: S101
        # And must include the "what's being lost" context that proves escalation
        assert "losing planning, parallelization, and context isolation" in messages[-1]  # noqa: S101


# ---------------------------------------------------------------------------
# Counter persistence
# ---------------------------------------------------------------------------


class TestCounterPersistence:
    def test_counter_persists_across_calls(self, tmp_path: Path) -> None:
        for _ in range(3):
            _run(_input("Bash"), tmp_path)
        counter = json.loads(
            (tmp_path / ".claude" / "state" / "delegation_violations.json").read_text()
        )
        assert counter["violations"] == 3  # noqa: S101

    def test_fresh_project_starts_at_zero(self, tmp_path: Path) -> None:
        _run(_input("Bash"), tmp_path)
        counter = json.loads(
            (tmp_path / ".claude" / "state" / "delegation_violations.json").read_text()
        )
        assert counter["violations"] == 1  # noqa: S101


# ---------------------------------------------------------------------------
# Subagent immunity
# ---------------------------------------------------------------------------


class TestSubagentImmunity:
    def test_parent_session_id_skips(self, tmp_path: Path) -> None:
        _, stderr, rc = _run(
            _input("Bash"),
            tmp_path,
            env_extra={"CLAUDE_PARENT_SESSION_ID": "abc123"},
        )
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101

    def test_agent_id_skips(self, tmp_path: Path) -> None:
        _, stderr, rc = _run(
            _input("Bash"),
            tmp_path,
            env_extra={"CLAUDE_AGENT_ID": "xyz"},
        )
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101

    def test_subagent_does_not_increment_counter(self, tmp_path: Path) -> None:
        _run(
            _input("Bash"),
            tmp_path,
            env_extra={"CLAUDE_PARENT_SESSION_ID": "x"},
        )
        counter_file = tmp_path / ".claude" / "state" / "delegation_violations.json"
        assert not counter_file.exists()  # noqa: S101


# ---------------------------------------------------------------------------
# delegation_active flag suppresses nudges
# ---------------------------------------------------------------------------


class TestDelegationActiveFlag:
    def test_active_flag_suppresses_nudge(self, tmp_path: Path) -> None:
        state = tmp_path / ".claude" / "state"
        state.mkdir(parents=True)
        (state / "delegation_active").touch()
        _, stderr, rc = _run(_input("Bash"), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101
