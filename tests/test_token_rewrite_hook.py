"""Comprehensive tests for token_rewrite_hook.py PreToolUse hook."""
# ruff: noqa: S101

import io
import json
from types import ModuleType

import pytest  # pyright: ignore[reportMissingImports]


# ---------------------------------------------------------------------------
# _has_shell_meta tests
# ---------------------------------------------------------------------------


class TestHasShellMeta:
    """Tests for _has_shell_meta(command)."""

    @pytest.mark.parametrize(
        "command",
        [
            "git push",
            "pytest tests/",
            "npm test",
            "cargo test --release",
            "go test ./...",
        ],
        ids=["git_push", "pytest", "npm_test", "cargo_test", "go_test"],
    )
    def test_clean_commands_return_false(
        self, token_rewrite_hook: ModuleType, command: str
    ) -> None:
        assert token_rewrite_hook._has_shell_meta(command) is False

    @pytest.mark.parametrize(
        ("command", "meta_id"),
        [
            ("git push | head", "pipe"),
            ("git push && echo done", "and"),
            ("git push || true", "or"),
            ("git push; echo", "semicolon"),
            ("cat <<EOF", "heredoc"),
            ("echo $(date)", "subshell"),
            ("git push > /dev/null", "redirect"),
            ("echo `date`", "backtick"),
            ("git push &", "background"),
        ],
    )
    def test_shell_meta_detected(
        self, token_rewrite_hook: ModuleType, command: str, meta_id: str
    ) -> None:
        assert token_rewrite_hook._has_shell_meta(command) is True


# ---------------------------------------------------------------------------
# _should_wrap tests
# ---------------------------------------------------------------------------


class TestShouldWrap:
    """Tests for _should_wrap(command)."""

    @pytest.mark.parametrize(
        "command",
        [
            # git subcommands
            "git push origin main",
            "git pull --rebase",
            "git fetch --all",
            "git add -A",
            "git commit -m 'msg'",
            "git merge feature",
            "git rebase main",
            "git stash pop",
            # pytest / py.test
            "pytest tests/",
            "pytest -x -v tests/unit",
            "py.test",
            "py.test tests/ -k test_foo",
            # cargo
            "cargo test",
            "cargo test --release",
            # npm / pnpm / yarn / bun
            "npm test",
            "pnpm test",
            "yarn test",
            "bun test",
            # npx runners
            "npx vitest run",
            "npx jest --coverage",
            "npx mocha tests/",
            "npx playwright test",
            "npx eslint src/",
            "npx next lint",
            "npx tsc --noEmit",
            # next standalone
            "next lint",
            # go
            "go test ./...",
            # make
            "make test",
            "make check",
            # container logs
            "docker logs my-container",
            "kubectl logs pod/my-pod",
            "podman logs ctr",
        ],
        ids=[
            "git_push",
            "git_pull",
            "git_fetch",
            "git_add",
            "git_commit",
            "git_merge",
            "git_rebase",
            "git_stash",
            "pytest",
            "pytest_flags",
            "py.test",
            "py.test_flags",
            "cargo_test",
            "cargo_test_release",
            "npm_test",
            "pnpm_test",
            "yarn_test",
            "bun_test",
            "npx_vitest",
            "npx_jest",
            "npx_mocha",
            "npx_playwright",
            "npx_eslint",
            "npx_next",
            "npx_tsc",
            "next_lint",
            "go_test",
            "make_test",
            "make_check",
            "docker_logs",
            "kubectl_logs",
            "podman_logs",
        ],
    )
    def test_positive_matches(
        self, token_rewrite_hook: ModuleType, command: str
    ) -> None:
        assert token_rewrite_hook._should_wrap(command) is True

    @pytest.mark.parametrize(
        "command",
        [
            # git non-wrappable subcommands
            "git status",
            "git log --oneline",
            "git diff HEAD",
            "git branch -a",
            # npm non-test
            "npm install",
            "npm run build",
            # cargo non-test
            "cargo build",
            "cargo clippy",
            # go non-test
            "go build ./...",
            "go run main.go",
            # make non-test
            "make build",
            "make clean",
            # npx non-test
            "npx prettier --write .",
            # general shell commands
            "ls -la",
            "echo hello",
            "cat file.txt",
            # empty string
            "",
        ],
        ids=[
            "git_status",
            "git_log",
            "git_diff",
            "git_branch",
            "npm_install",
            "npm_run_build",
            "cargo_build",
            "cargo_clippy",
            "go_build",
            "go_run",
            "make_build",
            "make_clean",
            "npx_prettier",
            "ls",
            "echo",
            "cat",
            "empty",
        ],
    )
    def test_negative_matches(
        self, token_rewrite_hook: ModuleType, command: str
    ) -> None:
        assert token_rewrite_hook._should_wrap(command) is False


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def _make_stdin(data: dict | str) -> io.StringIO:
    """Build a StringIO suitable for monkeypatching sys.stdin."""
    text = data if isinstance(data, str) else json.dumps(data)
    return io.StringIO(text)


class TestMain:
    """Tests for main() entry point."""

    def test_wrappable_bash_command_emits_rewrite(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin main"},
        }
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0

        out = capsys.readouterr().out.strip()
        result = json.loads(out)
        assert "updatedInput" in result
        cmd = result["updatedInput"]["command"]
        assert "compact_run.py" in cmd
        assert cmd.endswith("git push origin main")
        assert cmd.startswith("uv run --no-project --script ")

    def test_piped_command_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "git push | head"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_already_wrapped_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_input": {
                "command": "uv run --no-project --script /path/to/compact_run.py git push"
            },
        }
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    @pytest.mark.parametrize(
        "tool_name",
        ["Read", "Write", "Edit", "Grep", "Glob", "Agent"],
        ids=["Read", "Write", "Edit", "Grep", "Glob", "Agent"],
    )
    def test_non_bash_tool_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tool_name: str,
    ) -> None:
        payload = {"tool_name": tool_name, "tool_input": {"command": "git push"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_empty_command_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_empty_stdin_exits_zero(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_invalid_json_exits_zero(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("{not valid json"))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_missing_tool_name_exits_zero(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_input": {"command": "git push"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_missing_tool_input_exits_zero(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash"}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_disabled_via_env_var(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "git push"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "0")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_enabled_by_default_when_env_unset(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "pytest tests/"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.delenv("CLAUDE_TOKEN_EFFICIENCY", raising=False)

        rc = token_rewrite_hook.main()
        assert rc == 0

        out = capsys.readouterr().out.strip()
        result = json.loads(out)
        assert "updatedInput" in result
        assert "compact_run.py" in result["updatedInput"]["command"]

    def test_non_wrappable_bash_command_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""

    def test_output_json_format(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify the exact shape of the emitted JSON."""
        payload = {"tool_name": "Bash", "tool_input": {"command": "cargo test"}}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        token_rewrite_hook.main()

        out = capsys.readouterr().out.strip()
        result = json.loads(out)
        # Top-level key is updatedInput
        assert set(result.keys()) == {"updatedInput"}
        # updatedInput has exactly one key: command
        assert set(result["updatedInput"].keys()) == {"command"}
        cmd = result["updatedInput"]["command"]
        assert cmd.startswith("uv run --no-project --script ")
        assert "compact_run.py" in cmd
        assert cmd.endswith("cargo test")

    def test_tool_input_not_dict_passthrough(
        self,
        token_rewrite_hook: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When tool_input is a string instead of dict, should passthrough."""
        payload = {"tool_name": "Bash", "tool_input": "git push"}
        monkeypatch.setattr("sys.stdin", _make_stdin(payload))
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "1")

        rc = token_rewrite_hook.main()
        assert rc == 0
        assert capsys.readouterr().out.strip() == ""
