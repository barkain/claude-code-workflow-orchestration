"""Shared test fixtures for workflow-orchestrator plugin tests."""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest  # pyright: ignore[reportMissingImports]

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Resolved path to uv executable (avoids S607 partial path warnings)
_UV_BIN = shutil.which("uv") or "uv"


def load_module_from_file(name: str, path: Path) -> ModuleType:
    """Import a standalone script as a module (no package needed)."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # noqa: S101
        msg = f"Failed to create module spec for {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    # Don't add to sys.modules to avoid side effects between tests
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def compact_run() -> ModuleType:
    """Load compact_run.py as a module."""
    return load_module_from_file(
        "compact_run", PROJECT_ROOT / "hooks" / "compact_run.py"
    )


@pytest.fixture
def token_rewrite_hook() -> ModuleType:
    """Load token_rewrite_hook.py as a module."""
    return load_module_from_file(
        "token_rewrite_hook",
        PROJECT_ROOT / "hooks" / "PreToolUse" / "token_rewrite_hook.py",
    )


@pytest.fixture
def inject_token_efficiency() -> ModuleType:
    """Load inject_token_efficiency.py as a module."""
    return load_module_from_file(
        "inject_token_efficiency",
        PROJECT_ROOT / "hooks" / "SessionStart" / "inject_token_efficiency.py",
    )


@pytest.fixture
def run_hook():
    """Run a hook script via subprocess, returning (stdout, stderr, returncode)."""

    def _run(
        script_path: str | Path,
        stdin_data: str = "",
        env_override: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> tuple[str, str, int]:
        env = os.environ.copy()
        if env_override:
            env.update(env_override)
        result = subprocess.run(  # noqa: S603
            [_UV_BIN, "run", "--no-project", "--script", str(script_path)],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode

    return _run


@pytest.fixture
def run_compact_run():
    """Run compact_run.py with given command args via subprocess."""

    def _run(*cmd_args: str, timeout: int = 10) -> tuple[str, str, int]:
        result = subprocess.run(  # noqa: S603
            [
                _UV_BIN,
                "run",
                "--no-project",
                "--script",
                str(PROJECT_ROOT / "hooks" / "compact_run.py"),
                *cmd_args,
            ],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            cwd=str(PROJECT_ROOT),
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode

    return _run


@pytest.fixture
def make_hook_input():
    """Create JSON stdin for a PreToolUse hook."""

    def _make(tool_name: str, **tool_input: Any) -> str:
        return json.dumps({"tool_name": tool_name, "tool_input": tool_input})

    return _make
