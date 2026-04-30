import json
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from odoo_rich_cli.config import find_odoo_bin

SENTINEL = "__ODOO_CLI_RESULT__:"


def _venv_python() -> str:
    # Prefer $VIRTUAL_ENV so orc installed via `uv tool install` / `uvx` still
    # runs odoo-bin under the user's odoo venv, not its own isolated one.
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        for candidate in (
            Path(venv) / "bin" / "python",
            Path(venv) / "Scripts" / "python.exe",
            Path(venv) / "Scripts" / "python",
        ):
            if candidate.is_file():
                return str(candidate)
    return sys.executable


@dataclass
class ShellResult:
    success: bool
    message: str
    stdout: str
    stderr: str
    return_code: int
    data: Any = field(default=None)


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def _wrap_script(script: str) -> str:
    # The `env` pre-check turns odoo-bin's degraded "no DB loaded" shell into a
    # readable error instead of a NameError on the first env access.
    return f"""\
import json as _json

try:
    try:
        env
    except NameError:
        raise Exception(
            "No database loaded. odoo-bin shell could not auto-detect a database. "
            "Pass -d <database> or set db_name in odoo.conf."
        )
{_indent(script, 4)}
    try:
        _result
    except NameError:
        _result = {{"ok": True, "message": "Operation completed successfully."}}
except Exception as _e:
    _result = {{"ok": False, "message": str(_e)}}

print("{SENTINEL}" + _json.dumps(_result))
"""


def execute(
    script: str,
    config_path: str,
    database: str = "",
    timeout: int = 120,
) -> ShellResult:
    bin_path = find_odoo_bin()
    if bin_path is None:
        return ShellResult(False, "No odoo-bin found in the current directory.", "", "", -1)

    cmd = [_venv_python(), str(bin_path), "shell", "-c", config_path, "--no-http"]
    if database:
        cmd += ["-d", database]

    try:
        proc = subprocess.run(
            cmd, input=_wrap_script(script), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return ShellResult(False, f"Command timed out after {timeout} seconds.", "", "", -1)

    for line in proc.stdout.splitlines():
        if not line.startswith(SENTINEL):
            continue
        try:
            parsed = json.loads(line[len(SENTINEL) :])
        except json.JSONDecodeError:
            break
        return ShellResult(
            success=parsed.get("ok", False),
            message=parsed.get("message", ""),
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
            data=parsed.get("data"),
        )

    return ShellResult(
        success=proc.returncode == 0,
        message=proc.stderr.strip() or "No structured output received from odoo shell.",
        stdout=proc.stdout,
        stderr=proc.stderr,
        return_code=proc.returncode,
    )


def run_server(
    config_path: str,
    database: str,
    extra_args: Iterable[str] | None = None,
) -> int:
    bin_path = find_odoo_bin()
    if bin_path is None:
        return 1

    cmd = [_venv_python(), str(bin_path), "-c", config_path, "-d", database]
    if extra_args:
        cmd += list(extra_args)

    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        return 130
