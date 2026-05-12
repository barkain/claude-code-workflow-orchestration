"""Tests for hooks/PreToolUse/require_delegation.py (blocks work tools)."""

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
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
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


class TestBlocksWorkTools:
    @pytest.mark.parametrize(
        "tool",
        ["Bash", "Edit", "Write", "Glob", "Grep", "MultiEdit", "NotebookEdit"],
    )
    def test_work_tools_blocked(self, tmp_path: Path, tool: str) -> None:
        _, stderr, rc = _run(_input(tool), tmp_path)
        assert rc == 2  # noqa: S101
        assert "delegate" in stderr.lower()  # noqa: S101

    def test_read_allowed(self, tmp_path: Path) -> None:
        _, stderr, rc = _run(_input("Read"), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101

    @pytest.mark.parametrize(
        "tool",
        ["Agent", "Skill", "SlashCommand", "TaskCreate", "TaskUpdate",
         "EnterPlanMode", "ExitPlanMode", "ToolSearch", "TeamCreate",
         "SendMessage", "AskUserQuestion", "FooBar", "CronCreate"],
    )
    def test_non_work_tools_allowed(self, tmp_path: Path, tool: str) -> None:
        _, stderr, rc = _run(_input(tool), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101

    def test_empty_stdin_allowed(self, tmp_path: Path) -> None:
        _, _, rc = _run("", tmp_path)
        assert rc == 0  # noqa: S101

    def test_malformed_stdin_allowed(self, tmp_path: Path) -> None:
        _, _, rc = _run("not json", tmp_path)
        assert rc == 0  # noqa: S101


class TestSubagentImmunity:
    def test_parent_session_id_allows(self, tmp_path: Path) -> None:
        _, stderr, rc = _run(
            _input("Bash"), tmp_path,
            env_extra={"CLAUDE_PARENT_SESSION_ID": "abc123"},
        )
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101

    def test_agent_id_allows(self, tmp_path: Path) -> None:
        _, stderr, rc = _run(
            _input("Bash"), tmp_path,
            env_extra={"CLAUDE_AGENT_ID": "xyz"},
        )
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101


class TestDelegationActiveFlag:
    def test_active_flag_allows(self, tmp_path: Path) -> None:
        state = tmp_path / ".claude" / "state"
        state.mkdir(parents=True)
        (state / "delegation_active").touch()
        _, stderr, rc = _run(_input("Bash"), tmp_path)
        assert rc == 0  # noqa: S101
        assert stderr == ""  # noqa: S101
