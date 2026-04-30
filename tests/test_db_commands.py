from pathlib import Path
from unittest.mock import patch

from odoo_rich_cli import commands
from odoo_rich_cli.config import OdooConfig
from odoo_rich_cli.shell import ShellResult


def _cfg(tmp_path: Path) -> OdooConfig:
    return OdooConfig(db_name="dev", addons_path="", config_path=tmp_path / "odoo.conf")


def _ok() -> ShellResult:
    return ShellResult(True, "ok", "", "", 0)


def _captured_script(mock_execute: object) -> str:
    """Pull the script string out of the most recent execute() call."""
    return mock_execute.call_args[0][0]  # type: ignore[attr-defined]


def test_db_list_calls_list_dbs(tmp_path: Path) -> None:
    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_list(_cfg(tmp_path))

    script = _captured_script(mock)
    assert "list_dbs(force=True)" in script


def test_db_drop_refuses_connected_db(tmp_path: Path) -> None:
    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_drop(_cfg(tmp_path), "victim")

    script = _captured_script(mock)
    assert 'target = "victim"' in script
    assert "env.cr.dbname" in script  # the connected-DB guard is present
    assert "exp_drop(target)" in script


def test_db_backup_writes_to_path(tmp_path: Path) -> None:
    out = tmp_path / "snap.zip"
    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_backup(_cfg(tmp_path), "mydb", str(out))

    script = _captured_script(mock)
    assert 'target = "mydb"' in script
    assert repr(str(out)) in script  # the path is escaped via !r
    assert 'dump_db(target, _f, "zip")' in script
    # backup gets a longer timeout than the default 120s
    assert mock.call_args.kwargs["timeout"] == 600


def test_db_restore_passes_copy_flag(tmp_path: Path) -> None:
    src = tmp_path / "snap.zip"
    src.write_bytes(b"fake")

    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_restore(_cfg(tmp_path), "newdb", str(src), copy=True)

    script = _captured_script(mock)
    assert 'target = "newdb"' in script
    assert repr(str(src)) in script
    assert "copy=True" in script
    assert "restore_db(target, src, copy=True)" in script


def test_db_restore_default_copy_is_false(tmp_path: Path) -> None:
    src = tmp_path / "snap.zip"
    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_restore(_cfg(tmp_path), "newdb", str(src))

    assert "copy=False" in _captured_script(mock)


def test_db_duplicate_passes_both_names(tmp_path: Path) -> None:
    with patch("odoo_rich_cli.commands.execute", return_value=_ok()) as mock:
        commands.db_duplicate(_cfg(tmp_path), "src_db", "dst_db")

    script = _captured_script(mock)
    assert 'src = "src_db"' in script
    assert 'dst = "dst_db"' in script
    assert "exp_duplicate_database(src, dst)" in script
