"""Tests for hooks/compact_run.py -- output compression for CLI commands."""

from types import ModuleType
from unittest.mock import MagicMock

import pytest  # pyright: ignore[reportMissingImports]


# ---------------------------------------------------------------------------
# truncated_output
# ---------------------------------------------------------------------------
class TestTruncatedOutput:
    def test_under_limit(self, compact_run: ModuleType) -> None:
        content = "\n".join(f"line {i}" for i in range(10))
        assert compact_run.truncated_output(content) == content  # noqa: S101

    def test_at_limit(self, compact_run: ModuleType) -> None:
        content = "\n".join(f"line {i}" for i in range(compact_run.MAX_LINES))
        assert compact_run.truncated_output(content) == content  # noqa: S101

    def test_over_limit(self, compact_run: ModuleType) -> None:
        total = compact_run.MAX_LINES + 50
        lines = [f"line {i}" for i in range(total)]
        result = compact_run.truncated_output("\n".join(lines))
        expected_header = (
            f"[truncated: {total} lines total, showing last {compact_run.MAX_LINES}]"
        )
        assert result.startswith(expected_header)  # noqa: S101
        result_lines = result.splitlines()
        # header + MAX_LINES content lines
        assert len(result_lines) == compact_run.MAX_LINES + 1  # noqa: S101
        assert result_lines[-1] == f"line {total - 1}"  # noqa: S101

    def test_empty_string(self, compact_run: ModuleType) -> None:
        assert compact_run.truncated_output("") == ""  # noqa: S101


# ---------------------------------------------------------------------------
# emit_failure
# ---------------------------------------------------------------------------
class TestEmitFailure:
    def test_shows_stderr_and_truncated_stdout(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.emit_failure("some stdout", "some stderr", 42)
        assert code == 42  # noqa: S101
        captured = capsys.readouterr()
        assert "some stdout" in captured.out  # noqa: S101
        assert "some stderr" in captured.err  # noqa: S101

    def test_empty_streams(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.emit_failure("", "", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert captured.out == ""  # noqa: S101
        assert captured.err == ""  # noqa: S101


# ---------------------------------------------------------------------------
# handle_git
# ---------------------------------------------------------------------------
class TestHandleGit:
    def test_failure_returns_exit_code(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "push"], "stdout stuff", "error msg", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "error msg" in captured.err  # noqa: S101

    def test_push_extracts_branch(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stderr = "To github.com:user/repo.git\n   abc1234..def5678  main -> main\n"
        code = compact_run.handle_git(["git", "push"], "", stderr, 0)
        assert code == 0  # noqa: S101
        assert "main" in capsys.readouterr().out  # noqa: S101

    def test_push_no_branch_pattern_falls_back(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_result = MagicMock(returncode=0, stdout="feature-x\n")
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        code = compact_run.handle_git(["git", "push"], "", "", 0)
        assert code == 0  # noqa: S101
        assert "feature-x" in capsys.readouterr().out  # noqa: S101

    def test_pull_file_changed(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "Updating abc..def\nFast-forward\n 3 files changed, 10 insertions(+)\n"
        code = compact_run.handle_git(["git", "pull"], stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "3 files changed" in out  # noqa: S101

    def test_pull_already_up_to_date(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "pull"], "Already up to date.\n", "", 0)
        assert code == 0  # noqa: S101
        assert "already up to date" in capsys.readouterr().out  # noqa: S101

    def test_pull_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "pull"], "some output\n", "", 0)
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_commit_extracts_hash_and_message(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "[main abc1234] Fix the bug\n 1 file changed\n"
        code = compact_run.handle_git(["git", "commit"], stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "abc1234" in out  # noqa: S101
        assert "Fix the bug" in out  # noqa: S101

    def test_commit_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "commit"], "weird output", "", 0)
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_add_success(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "add", "."], "", "", 0)
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_fetch_new_refs(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stderr = (
            "From github.com:user/repo\n"
            " [new branch]      feature -> origin/feature\n"
            " -> origin/main\n"
        )
        code = compact_run.handle_git(["git", "fetch"], "", stderr, 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "3 new refs" in out  # noqa: S101

    def test_fetch_zero_refs(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "fetch"], "", "", 0)
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_merge_already_up_to_date(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "merge"], "Already up to date.\n", "", 0)
        assert code == 0  # noqa: S101
        assert "already up to date" in capsys.readouterr().out  # noqa: S101

    def test_merge_file_changed(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = (
            "Merge made by the 'ort' strategy.\n 2 files changed, 5 insertions(+)\n"
        )
        code = compact_run.handle_git(["git", "merge"], stdout, "", 0)
        assert code == 0  # noqa: S101
        assert "2 files changed" in capsys.readouterr().out  # noqa: S101

    def test_merge_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "merge"], "some output\n", "", 0)
        assert code == 0  # noqa: S101
        assert "merged" in capsys.readouterr().out  # noqa: S101

    def test_rebase_success(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "Successfully rebased and updated refs/heads/main.\n"
        code = compact_run.handle_git(["git", "rebase"], stdout, "", 0)
        assert code == 0  # noqa: S101
        assert "Successfully rebased" in capsys.readouterr().out  # noqa: S101

    def test_rebase_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "rebase"], "done\n", "", 0)
        assert code == 0  # noqa: S101
        assert "rebased" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize(
        ("stdout", "expected"),
        [
            ("Saved working directory and index state", "stashed"),
            ("Dropped refs/stash@{0}", "dropped"),
            ("No local changes to save", "nothing to stash"),
        ],
    )
    def test_stash_variants(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        stdout: str,
        expected: str,
    ) -> None:
        code = compact_run.handle_git(["git", "stash"], stdout, "", 0)
        assert code == 0  # noqa: S101
        assert expected in capsys.readouterr().out  # noqa: S101

    def test_stash_list_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = (
            "stash@{0}: WIP on main: abc1234 msg\nstash@{1}: WIP on dev: def5678 msg2\n"
        )
        code = compact_run.handle_git(["git", "stash", "list"], stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "stash@{0}" in out  # noqa: S101
        assert "stash@{1}" in out  # noqa: S101

    def test_unknown_subcommand_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git", "status"], "M file.py\n", "", 0)
        assert code == 0  # noqa: S101
        assert "M file.py" in capsys.readouterr().out  # noqa: S101

    def test_no_subcommand(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_git(["git"], "usage info\n", "", 0)
        assert code == 0  # noqa: S101
        assert "usage info" in capsys.readouterr().out  # noqa: S101


# ---------------------------------------------------------------------------
# handle_container_logs
# ---------------------------------------------------------------------------
class TestHandleContainerLogs:
    def test_failure(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_container_logs("out", "err", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "err" in captured.err  # noqa: S101

    def test_dedup_consecutive_lines(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        lines = ["line A", "line A", "line A", "line B"]
        stdout = "\n".join(lines)
        code = compact_run.handle_container_logs(stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "[repeated 3 times]" in out  # noqa: S101
        assert "line B" in out  # noqa: S101

    def test_tail_truncation_with_dedup(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Create enough unique lines to exceed LOG_TAIL after dedup
        lines = [f"unique line {i}" for i in range(80)]
        stdout = "\n".join(lines)
        code = compact_run.handle_container_logs(stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert f"showing last {compact_run.LOG_TAIL}" in out  # noqa: S101

    def test_no_dedup_mode(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(compact_run, "LOG_DEDUP", False)
        lines = [f"line {i}" for i in range(10)]
        stdout = "\n".join(lines)
        code = compact_run.handle_container_logs(stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        assert "line 0" in out  # noqa: S101
        assert "line 9" in out  # noqa: S101

    def test_no_dedup_tail(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(compact_run, "LOG_DEDUP", False)
        lines = [f"line {i}" for i in range(100)]
        stdout = "\n".join(lines)
        code = compact_run.handle_container_logs(stdout, "", 0)
        assert code == 0  # noqa: S101
        out = capsys.readouterr().out
        # Should only show last LOG_TAIL lines
        assert "line 99" in out  # noqa: S101
        assert "line 0" not in out  # noqa: S101


# ---------------------------------------------------------------------------
# handle_pytest
# ---------------------------------------------------------------------------
class TestHandlePytest:
    def test_success_extracts_summary(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "collected 42 items\n\n....\n\n42 passed in 1.23s\n"
        code = compact_run.handle_pytest(stdout, "", 0)
        assert code == 0  # noqa: S101
        assert "42 passed in 1.23s" in capsys.readouterr().out  # noqa: S101

    def test_success_no_match_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_pytest("all good\n", "", 0)
        assert code == 0  # noqa: S101
        assert "all passed" in capsys.readouterr().out  # noqa: S101

    def test_failure_with_failures_section(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = (
            "collected 5 items\n"
            "===== FAILURES =====\n"
            "test_foo FAILED\n"
            "AssertionError: assert 1 == 2\n"
            "===== short test summary =====\n"
            "FAILED test_foo.py::test_foo\n"
        )
        code = compact_run.handle_pytest(stdout, "", 1)
        assert code == 1  # noqa: S101
        out = capsys.readouterr().out
        assert "FAILURES" in out  # noqa: S101
        assert "FAILED" in out  # noqa: S101

    def test_failure_without_failures_section(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "ERROR collecting test_foo.py\n"
        code = compact_run.handle_pytest(stdout, "import error", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "import error" in captured.err  # noqa: S101

    def test_failure_with_stderr(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = (
            "===== FAILURES =====\n"
            "test_bar FAILED\n"
            "===== short test summary =====\n"
            "FAILED test_bar\n"
        )
        code = compact_run.handle_pytest(stdout, "warning text", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "warning text" in captured.err  # noqa: S101


# ---------------------------------------------------------------------------
# handle_cargo
# ---------------------------------------------------------------------------
class TestHandleCargo:
    def test_cargo_test_success(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "running 10 tests\n...........\ntest result: ok. 10 passed; 0 failed\n"
        code = compact_run.handle_cargo(["cargo", "test"], stdout, "", 0)
        assert code == 0  # noqa: S101
        assert "10 passed" in capsys.readouterr().out  # noqa: S101

    def test_cargo_test_success_no_match(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_cargo(["cargo", "test"], "ok done\n", "", 0)
        assert code == 0  # noqa: S101
        assert "all passed" in capsys.readouterr().out  # noqa: S101

    def test_cargo_test_failure_with_failures(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = (
            "test my_test FAILED\n"
            "---- my_test ---\n"
            "thread 'main' panicked at 'assert failed'\n"
            "failures:\n"
            "test result: FAILED. 1 passed; 1 failed\n"
        )
        code = compact_run.handle_cargo(["cargo", "test"], stdout, "", 1)
        assert code == 1  # noqa: S101
        out = capsys.readouterr().out
        assert "FAILED" in out  # noqa: S101

    def test_cargo_test_failure_no_failures_pattern(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_cargo(
            ["cargo", "test"], "compile error\n", "build failed\n", 1
        )
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "build failed" in captured.err  # noqa: S101

    def test_cargo_build_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_cargo(
            ["cargo", "build"], "compiled stuff\n", "warnings\n", 0
        )
        assert code == 0  # noqa: S101
        captured = capsys.readouterr()
        assert "compiled stuff" in captured.out  # noqa: S101
        assert "warnings" in captured.err  # noqa: S101

    def test_cargo_no_subcommand(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_cargo(["cargo"], "usage\n", "", 0)
        assert code == 0  # noqa: S101
        assert "usage" in capsys.readouterr().out  # noqa: S101


# ---------------------------------------------------------------------------
# handle_node_test
# ---------------------------------------------------------------------------
class TestHandleNodeTest:
    @pytest.mark.parametrize(
        ("stdout", "expected"),
        [
            ("Tests: 5 passed", "Tests: 5 passed"),
            ("10 passing (2s)", "10 passing"),
            ("test suites: 3 passed, 3 total", "test suites: 3 passed"),
            ("42 tests passed", "42 tests passed"),
        ],
    )
    def test_success_formats(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        stdout: str,
        expected: str,
    ) -> None:
        code = compact_run.handle_node_test(stdout, "", 0)
        assert code == 0  # noqa: S101
        assert expected in capsys.readouterr().out  # noqa: S101

    def test_success_fallback(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_node_test("done\n", "", 0)
        assert code == 0  # noqa: S101
        assert "all passed" in capsys.readouterr().out  # noqa: S101

    def test_failure(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_node_test("FAIL test.js", "error", 1)
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "error" in captured.err  # noqa: S101


# ---------------------------------------------------------------------------
# handle_npx
# ---------------------------------------------------------------------------
class TestHandleNpx:
    @pytest.mark.parametrize("runner", ["vitest", "jest", "mocha", "playwright"])
    def test_known_runner_success(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        runner: str,
    ) -> None:
        code = compact_run.handle_npx(["npx", runner], "Tests: 5 passed\n", "", 0)
        assert code == 0  # noqa: S101
        assert "5 passed" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("runner", ["vitest", "jest", "mocha", "playwright"])
    def test_known_runner_failure(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        runner: str,
    ) -> None:
        code = compact_run.handle_npx(["npx", runner], "FAIL", "test error", 1)
        assert code == 1  # noqa: S101
        assert "test error" in capsys.readouterr().err  # noqa: S101

    def test_lint_runner_success_eslint(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        code = compact_run.handle_npx(["npx", "eslint", "."], "lint output\n", "", 0)
        assert code == 0  # noqa: S101
        assert "no issues" in capsys.readouterr().out  # noqa: S101

    def test_lint_runner_success_next(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        code = compact_run.handle_npx(["npx", "next", "lint"], "lint output\n", "", 0)
        assert code == 0  # noqa: S101
        assert "no issues" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("runner", ["eslint", "next"])
    def test_lint_runner_failure(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        runner: str,
    ) -> None:
        code = compact_run.handle_npx(["npx", runner, "."], "errors\n", "lint err\n", 1)
        assert code == 1  # noqa: S101
        assert "lint err" in capsys.readouterr().err  # noqa: S101

    def test_tsc_success(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_npx(["npx", "tsc", "--noEmit"], "", "", 0)
        assert code == 0  # noqa: S101
        assert "no type errors" in capsys.readouterr().out  # noqa: S101

    def test_tsc_failure(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_npx(
            ["npx", "tsc", "--noEmit"], "src/foo.ts(1,1): error TS2345\n", "", 1
        )
        assert code == 1  # noqa: S101
        assert "error TS2345" in capsys.readouterr().out  # noqa: S101

    def test_other_npx_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_npx(
            ["npx", "prettier", "."], "lint output\n", "warn\n", 0
        )
        assert code == 0  # noqa: S101
        captured = capsys.readouterr()
        assert "lint output" in captured.out  # noqa: S101
        assert "warn" in captured.err  # noqa: S101

    def test_no_subcommand_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_npx(["npx"], "usage\n", "", 0)
        assert code == 0  # noqa: S101
        assert "usage" in capsys.readouterr().out  # noqa: S101


# ---------------------------------------------------------------------------
# handle_go
# ---------------------------------------------------------------------------
class TestHandleGo:
    def test_go_test_success(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "ok  \tgithub.com/user/pkg1\t0.5s\nok  \tgithub.com/user/pkg2\t1.2s\n"
        code = compact_run.handle_go(["go", "test", "./..."], stdout, "", 0)
        assert code == 0  # noqa: S101
        assert "2 packages passed" in capsys.readouterr().out  # noqa: S101

    def test_go_test_failure_with_failures(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdout = "--- FAIL: TestFoo (0.00s)\nFAIL\tgithub.com/user/pkg\n"
        code = compact_run.handle_go(["go", "test"], stdout, "", 1)
        assert code == 1  # noqa: S101
        out = capsys.readouterr().out
        assert "FAIL" in out  # noqa: S101

    def test_go_test_failure_no_pattern(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_go(
            ["go", "test"], "build error\n", "compile fail\n", 1
        )
        assert code == 1  # noqa: S101
        captured = capsys.readouterr()
        assert "compile fail" in captured.err  # noqa: S101

    def test_go_build_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_go(
            ["go", "build"], "building...\n", "linker warn\n", 0
        )
        assert code == 0  # noqa: S101
        captured = capsys.readouterr()
        assert "building" in captured.out  # noqa: S101
        assert "linker warn" in captured.err  # noqa: S101

    def test_go_no_subcommand(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_go(["go"], "usage\n", "", 0)
        assert code == 0  # noqa: S101
        assert "usage" in capsys.readouterr().out  # noqa: S101


# ---------------------------------------------------------------------------
# handle_make
# ---------------------------------------------------------------------------
class TestHandleMake:
    @pytest.mark.parametrize("target", ["test", "check"])
    def test_make_test_success(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        target: str,
    ) -> None:
        code = compact_run.handle_make(["make", target], "output\n", "", 0)
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    @pytest.mark.parametrize("target", ["test", "check"])
    def test_make_test_failure(
        self,
        compact_run: ModuleType,
        capsys: pytest.CaptureFixture[str],
        target: str,
    ) -> None:
        code = compact_run.handle_make(["make", target], "fail out\n", "fail err\n", 2)
        assert code == 2  # noqa: S101
        captured = capsys.readouterr()
        assert "fail err" in captured.err  # noqa: S101

    def test_make_other_passthrough(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_make(["make", "build"], "compiling\n", "warn\n", 0)
        assert code == 0  # noqa: S101
        captured = capsys.readouterr()
        assert "compiling" in captured.out  # noqa: S101
        assert "warn" in captured.err  # noqa: S101

    def test_make_no_subcommand(
        self, compact_run: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = compact_run.handle_make(["make"], "usage\n", "", 0)
        assert code == 0  # noqa: S101
        assert "usage" in capsys.readouterr().out  # noqa: S101


# ---------------------------------------------------------------------------
# main() routing
# ---------------------------------------------------------------------------
class TestMain:
    def test_no_args_returns_1(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.argv", ["compact_run.py"])
        code = compact_run.main()
        assert code == 1  # noqa: S101
        assert "Usage" in capsys.readouterr().err  # noqa: S101

    def test_routes_git_to_handle_git(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "git", "add", "."])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_routes_git_with_path(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """git invoked via full path should still route to handle_git."""
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "/usr/bin/git", "add"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_routes_pytest(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="5 passed in 0.5s\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "pytest"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "5 passed" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("cmd", ["docker", "podman", "kubectl"])
    def test_routes_container_logs(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cmd: str,
    ) -> None:
        mock_result = MagicMock(stdout="log line 1\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", cmd, "logs", "mycontainer"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "log line 1" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("cmd", ["docker", "podman", "kubectl"])
    def test_container_non_logs_success(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cmd: str,
    ) -> None:
        mock_result = MagicMock(stdout="container list\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", cmd, "ps"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "container list" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("cmd", ["docker", "podman", "kubectl"])
    def test_container_non_logs_failure(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cmd: str,
    ) -> None:
        mock_result = MagicMock(stdout="", stderr="not found", returncode=1)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", cmd, "run", "img"])
        code = compact_run.main()
        assert code == 1  # noqa: S101

    @pytest.mark.parametrize("cmd", ["npm", "pnpm", "yarn", "bun"])
    def test_routes_node_test(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cmd: str,
    ) -> None:
        mock_result = MagicMock(stdout="Tests: 3 passed\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", cmd, "test"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "3 passed" in capsys.readouterr().out  # noqa: S101

    @pytest.mark.parametrize("cmd", ["npm", "pnpm", "yarn", "bun"])
    def test_node_non_test_passthrough(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cmd: str,
    ) -> None:
        mock_result = MagicMock(stdout="installed\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", cmd, "install"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "installed" in capsys.readouterr().out  # noqa: S101

    def test_routes_npx(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="Tests: 8 passed\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "npx", "vitest"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "8 passed" in capsys.readouterr().out  # noqa: S101

    def test_routes_cargo(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(
            stdout="test result: ok. 5 passed; 0 failed\n", stderr="", returncode=0
        )
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "cargo", "test"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "5 passed" in capsys.readouterr().out  # noqa: S101

    def test_routes_go(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="ok  \tpkg\t0.1s\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "go", "test"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert "1 packages passed" in capsys.readouterr().out  # noqa: S101

    def test_routes_make(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="done\n", stderr="", returncode=0)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "make", "test"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        assert capsys.readouterr().out.strip() == "ok"  # noqa: S101

    def test_unknown_command_fallback(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(
            stdout="some output\n", stderr="some warning\n", returncode=0
        )
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "ls", "-la"])
        code = compact_run.main()
        assert code == 0  # noqa: S101
        captured = capsys.readouterr()
        assert "some output" in captured.out  # noqa: S101
        assert "some warning" in captured.err  # noqa: S101

    def test_file_not_found_returns_1(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def raise_fnf(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("no such file")

        monkeypatch.setattr(compact_run.subprocess, "run", raise_fnf)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "nonexistent"])
        code = compact_run.main()
        assert code == 1  # noqa: S101  # Hook-compliant exit code (0/1/2 only)
        assert "command not found" in capsys.readouterr().err  # noqa: S101

    def test_oserror_returns_1(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def raise_os(*_args: object, **_kwargs: object) -> None:
            raise OSError("permission denied")

        monkeypatch.setattr(compact_run.subprocess, "run", raise_os)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "badcmd"])
        code = compact_run.main()
        assert code == 1  # noqa: S101
        assert "error running command" in capsys.readouterr().err  # noqa: S101

    def test_fallback_preserves_exit_code(
        self,
        compact_run: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_result = MagicMock(stdout="", stderr="err\n", returncode=42)
        monkeypatch.setattr(compact_run.subprocess, "run", lambda *a, **kw: mock_result)
        monkeypatch.setattr("sys.argv", ["compact_run.py", "unknown_cmd"])
        code = compact_run.main()
        assert code == 42  # noqa: S101
