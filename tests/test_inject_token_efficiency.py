"""Unit tests for hooks/SessionStart/inject_token_efficiency.py."""

import json
import sys
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest  # pyright: ignore[reportMissingImports]


def _module_file(mod: ModuleType) -> str:
    """Get __file__ from module, raising if unavailable."""
    f = mod.__file__
    if f is None:  # noqa: S101
        msg = "Module has no __file__ attribute"
        raise RuntimeError(msg)
    return f


# ---------------------------------------------------------------------------
# get_plugin_root()
# ---------------------------------------------------------------------------


class TestGetPluginRoot:
    """Tests for get_plugin_root() resolution logic."""

    def test_returns_env_var_when_set(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/custom/plugin/root")
        result = inject_token_efficiency.get_plugin_root()
        assert result == Path("/custom/plugin/root")  # noqa: S101

    def test_returns_three_levels_up_without_env_var(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        result = inject_token_efficiency.get_plugin_root()
        script_path = Path(_module_file(inject_token_efficiency)).resolve()
        expected = script_path.parent.parent.parent
        assert result == expected  # noqa: S101


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() entry point."""

    def test_default_enabled_outputs_valid_json(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default (enabled): outputs valid JSON with md file content."""
        monkeypatch.delenv("CLAUDE_TOKEN_EFFICIENCY", raising=False)
        project_root = (
            Path(_module_file(inject_token_efficiency)).resolve().parent.parent.parent
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(project_root))

        captured = StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        rc = inject_token_efficiency.main()

        assert rc == 0  # noqa: S101
        output = json.loads(captured.getvalue())
        assert "hookSpecificOutput" in output  # noqa: S101
        hook_output = output["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "SessionStart"  # noqa: S101
        assert "additionalContext" in hook_output  # noqa: S101
        assert "git status -sb" in hook_output["additionalContext"]  # noqa: S101

    def test_disabled_via_env_var(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CLAUDE_TOKEN_EFFICIENCY=0: exits 0, no stdout."""
        monkeypatch.setenv("CLAUDE_TOKEN_EFFICIENCY", "0")

        captured = StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        rc = inject_token_efficiency.main()

        assert rc == 0  # noqa: S101
        assert captured.getvalue() == ""  # noqa: S101

    def test_file_not_found(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """File not found: exits 0, warning on stderr."""
        monkeypatch.delenv("CLAUDE_TOKEN_EFFICIENCY", raising=False)
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        captured_out = StringIO()
        captured_err = StringIO()
        monkeypatch.setattr(sys, "stdout", captured_out)
        monkeypatch.setattr(sys, "stderr", captured_err)

        rc = inject_token_efficiency.main()

        assert rc == 0  # noqa: S101
        assert captured_out.getvalue() == ""  # noqa: S101
        assert "not found" in captured_err.getvalue().lower()  # noqa: S101

    def test_file_read_error(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """File read error (OSError): exits 0, warning on stderr."""
        monkeypatch.delenv("CLAUDE_TOKEN_EFFICIENCY", raising=False)
        md_path = tmp_path / "system-prompts" / "token_efficient_cli.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("placeholder")
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        captured_out = StringIO()
        captured_err = StringIO()
        monkeypatch.setattr(sys, "stdout", captured_out)
        monkeypatch.setattr(sys, "stderr", captured_err)

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            rc = inject_token_efficiency.main()

        assert rc == 0  # noqa: S101
        assert captured_out.getvalue() == ""  # noqa: S101
        assert "warning" in captured_err.getvalue().lower()  # noqa: S101

    def test_json_structure(
        self,
        inject_token_efficiency: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify exact JSON structure matches expected schema."""
        monkeypatch.delenv("CLAUDE_TOKEN_EFFICIENCY", raising=False)
        project_root = (
            Path(_module_file(inject_token_efficiency)).resolve().parent.parent.parent
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(project_root))

        captured = StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        inject_token_efficiency.main()

        output = json.loads(captured.getvalue())
        assert set(output.keys()) == {"hookSpecificOutput"}  # noqa: S101
        assert set(output["hookSpecificOutput"].keys()) == {  # noqa: S101
            "hookEventName",
            "additionalContext",
        }
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"  # noqa: S101
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)  # noqa: S101
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0  # noqa: S101
