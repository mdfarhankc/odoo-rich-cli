import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from odoo_rich_cli import shell
from odoo_rich_cli.shell import SENTINEL, ShellResult, _venv_python, execute, run_server


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


def _patch_bin(tmp_path: Path) -> Any:
    bin_path = tmp_path / "odoo-bin"
    bin_path.write_text("#!/usr/bin/env python\n")
    return patch("odoo_rich_cli.shell.find_odoo_bin", return_value=bin_path)


def test_execute_parses_sentinel_success(tmp_path: Path) -> None:
    payload = json.dumps({"ok": True, "message": "ok!", "data": {"x": 1}})
    proc = _completed(stdout=f"some startup noise\n{SENTINEL}{payload}\nmore noise\n")

    with _patch_bin(tmp_path), patch("subprocess.run", return_value=proc):
        result = execute("script", "/tmp/odoo.conf", "my_db")

    assert result.success is True
    assert result.message == "ok!"
    assert result.data == {"x": 1}


def test_execute_parses_sentinel_failure(tmp_path: Path) -> None:
    payload = json.dumps({"ok": False, "message": "boom"})
    proc = _completed(stdout=f"{SENTINEL}{payload}\n")

    with _patch_bin(tmp_path), patch("subprocess.run", return_value=proc):
        result = execute("script", "/tmp/odoo.conf", "my_db")

    assert result.success is False
    assert result.message == "boom"


def test_execute_falls_back_to_stderr_when_no_sentinel(tmp_path: Path) -> None:
    proc = _completed(stdout="no sentinel here\n", stderr="ImportError: …\n", returncode=1)

    with _patch_bin(tmp_path), patch("subprocess.run", return_value=proc):
        result = execute("script", "/tmp/odoo.conf", "my_db")

    assert result.success is False
    assert "ImportError" in result.message


def test_execute_returns_failure_when_no_odoo_bin() -> None:
    with patch("odoo_rich_cli.shell.find_odoo_bin", return_value=None):
        result = execute("script", "/tmp/odoo.conf", "my_db")

    assert result.success is False
    assert "No odoo-bin" in result.message


def test_execute_handles_timeout(tmp_path: Path) -> None:
    with (
        _patch_bin(tmp_path),
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="odoo-bin", timeout=1),
        ),
    ):
        result = execute("script", "/tmp/odoo.conf", "my_db", timeout=1)

    assert result.success is False
    assert "timed out" in result.message


def test_execute_omits_d_flag_when_database_is_empty(tmp_path: Path) -> None:
    payload = json.dumps({"ok": True, "message": "ok"})
    proc = _completed(stdout=f"{SENTINEL}{payload}\n")

    with _patch_bin(tmp_path), patch("subprocess.run", return_value=proc) as mock_run:
        execute("script", "/tmp/odoo.conf", "")

    cmd = mock_run.call_args[0][0]
    assert "-d" not in cmd


def test_run_server_returns_subprocess_returncode(tmp_path: Path) -> None:
    proc = _completed(returncode=0)

    with _patch_bin(tmp_path), patch("subprocess.run", return_value=proc):
        assert run_server("/tmp/odoo.conf", "my_db") == 0


def test_run_server_returns_130_on_keyboard_interrupt(tmp_path: Path) -> None:
    with _patch_bin(tmp_path), patch("subprocess.run", side_effect=KeyboardInterrupt):
        assert run_server("/tmp/odoo.conf", "my_db") == 130


def test_run_server_returns_1_when_no_odoo_bin() -> None:
    with patch("odoo_rich_cli.shell.find_odoo_bin", return_value=None):
        assert run_server("/tmp/odoo.conf", "my_db") == 1


def test_venv_python_falls_back_to_sys_executable_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert _venv_python() == sys.executable


def test_venv_python_picks_venv_python_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create a fake venv layout with the platform-appropriate python
    if sys.platform == "win32":
        py = tmp_path / "Scripts" / "python.exe"
    else:
        py = tmp_path / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("")

    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))
    assert _venv_python() == str(py)


def test_shell_result_dataclass_round_trips() -> None:
    r = ShellResult(success=True, message="hi", stdout="", stderr="", return_code=0, data=[1, 2])
    assert r.data == [1, 2]
    # `shell` module is exposed as expected
    assert hasattr(shell, "execute")
