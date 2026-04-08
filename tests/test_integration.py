"""Integration tests for hook scripts (run via uv subprocess)."""

import json
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# compact_run.py integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCompactRunIntegration:
    """Integration tests for hooks/compact_run.py."""

    def test_echo_passthrough(self, run_compact_run) -> None:
        """echo hello: passthrough, exit 0, stdout contains 'hello'."""
        stdout, _stderr, rc = run_compact_run("echo", "hello")
        assert rc == 0  # noqa: S101
        assert "hello" in stdout  # noqa: S101

    def test_no_args_exits_with_error(self, run_compact_run) -> None:
        """No args: exit 1, stderr contains usage."""
        _stdout, stderr, rc = run_compact_run()
        assert rc == 1  # noqa: S101
        assert "usage" in stderr.lower()  # noqa: S101

    def test_nonexistent_command(self, run_compact_run) -> None:
        """Nonexistent command: exit 127 or similar non-zero."""
        _stdout, _stderr, rc = run_compact_run("nonexistent_command_xyz")
        assert rc != 0  # noqa: S101


# ---------------------------------------------------------------------------
# token_rewrite_hook.py integration
# ---------------------------------------------------------------------------

REWRITE_HOOK = PROJECT_ROOT / "hooks" / "PreToolUse" / "token_rewrite_hook.py"


@pytest.mark.integration
class TestTokenRewriteHookIntegration:
    """Integration tests for hooks/PreToolUse/token_rewrite_hook.py."""

    def test_git_push_rewritten(self, run_hook) -> None:
        """git push command should be rewritten with --quiet."""
        stdin_data = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git push"}}
        )
        stdout, _stderr, rc = run_hook(REWRITE_HOOK, stdin_data=stdin_data)
        assert rc == 0  # noqa: S101
        assert "updatedInput" in stdout  # noqa: S101

    def test_passthrough_no_rewrite(self, run_hook) -> None:
        """git status | head should pass through (no rewrite)."""
        stdin_data = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git status | head"}}
        )
        stdout, _stderr, rc = run_hook(REWRITE_HOOK, stdin_data=stdin_data)
        assert rc == 0  # noqa: S101
        assert stdout.strip() == ""  # noqa: S101

    def test_non_bash_tool_passthrough(self, run_hook) -> None:
        """Read tool: empty stdout (passthrough)."""
        stdin_data = json.dumps(
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}  # noqa: S108
        )
        stdout, _stderr, rc = run_hook(REWRITE_HOOK, stdin_data=stdin_data)
        assert rc == 0  # noqa: S101
        assert stdout.strip() == ""  # noqa: S101

    def test_disabled_via_env_var(self, run_hook) -> None:
        """CLAUDE_TOKEN_EFFICIENCY=0: empty stdout for any input."""
        stdin_data = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git push"}}
        )
        stdout, _stderr, rc = run_hook(
            REWRITE_HOOK,
            stdin_data=stdin_data,
            env_override={"CLAUDE_TOKEN_EFFICIENCY": "0"},
        )
        assert rc == 0  # noqa: S101
        assert stdout.strip() == ""  # noqa: S101


# ---------------------------------------------------------------------------
# inject_all.py (consolidated SessionStart) integration
# ---------------------------------------------------------------------------

INJECT_HOOK = PROJECT_ROOT / "hooks" / "SessionStart" / "inject_all.py"


@pytest.mark.integration
class TestInjectAllIntegration:
    """Integration tests for hooks/SessionStart/inject_all.py token-efficiency injection."""

    def test_default_outputs_json(self, run_hook) -> None:
        """Default: stdout is valid JSON with hookSpecificOutput."""
        stdout, _stderr, rc = run_hook(INJECT_HOOK)
        assert rc == 0  # noqa: S101
        output = json.loads(stdout)
        assert "hookSpecificOutput" in output  # noqa: S101
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"  # noqa: S101
        assert "additionalContext" in output["hookSpecificOutput"]  # noqa: S101

    def test_disabled_via_env_var(self, run_hook) -> None:
        """CLAUDE_TOKEN_EFFICIENCY=0: token-efficiency content omitted from merged context."""
        stdout, _stderr, rc = run_hook(
            INJECT_HOOK,
            env_override={"CLAUDE_TOKEN_EFFICIENCY": "0"},
        )
        assert rc == 0  # noqa: S101
        # Other sections (orchestrator stub, output style) still inject; token content must not.
        if stdout.strip():
            output = json.loads(stdout)
            content = output["hookSpecificOutput"]["additionalContext"]
            assert "git status -sb" not in content  # noqa: S101

    def test_contains_known_content(self, run_hook) -> None:
        """JSON contains actual content from token_efficient_cli.md when enabled."""
        stdout, _stderr, rc = run_hook(INJECT_HOOK)
        assert rc == 0  # noqa: S101
        output = json.loads(stdout)
        content = output["hookSpecificOutput"]["additionalContext"]
        assert "compact_run.py" in content  # noqa: S101
