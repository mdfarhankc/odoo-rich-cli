from pathlib import Path

import pytest

from odoo_rich_cli.config import (
    find_config,
    find_odoo_bin,
    parse_config,
    require_odoo_project,
    resolve_config,
)


def _write_conf(path: Path, body: str) -> Path:
    conf = path / "odoo.conf"
    conf.write_text(body, encoding="utf-8")
    return conf


def test_parse_reads_db_name_and_addons(tmp_path: Path) -> None:
    conf = _write_conf(
        tmp_path,
        "[options]\ndb_name = my_db\naddons_path = /opt/odoo/addons\n",
    )
    cfg = parse_config(conf)
    assert cfg.db_name == "my_db"
    assert cfg.addons_path == "/opt/odoo/addons"
    assert cfg.config_path == conf


@pytest.mark.parametrize("falsy", ["False", "false", "None", "none"])
def test_parse_treats_odoo_falsy_strings_as_empty(tmp_path: Path, falsy: str) -> None:
    conf = _write_conf(tmp_path, f"[options]\ndb_name = {falsy}\n")
    cfg = parse_config(conf)
    assert cfg.db_name == ""


def test_parse_handles_missing_options_section(tmp_path: Path) -> None:
    conf = _write_conf(tmp_path, "")
    cfg = parse_config(conf)
    assert cfg.db_name == ""
    assert cfg.addons_path == ""


def test_find_config_returns_existing(tmp_path: Path) -> None:
    conf = _write_conf(tmp_path, "")
    assert find_config(tmp_path) == conf


def test_find_config_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"No odoo\.conf"):
        find_config(tmp_path)


def test_resolve_uses_database_override(tmp_path: Path) -> None:
    _write_conf(tmp_path, "[options]\ndb_name = from_conf\n")
    cfg = resolve_config(str(tmp_path / "odoo.conf"), database="override")
    assert cfg.db_name == "override"


def test_resolve_requires_db_name_somewhere(tmp_path: Path) -> None:
    _write_conf(tmp_path, "[options]\ndb_name = False\n")
    with pytest.raises(ValueError, match="No database specified"):
        resolve_config(str(tmp_path / "odoo.conf"))


def test_find_odoo_bin_present_and_absent(tmp_path: Path) -> None:
    assert find_odoo_bin(tmp_path) is None
    (tmp_path / "odoo-bin").write_text("#!/usr/bin/env python\n")
    found = find_odoo_bin(tmp_path)
    assert found is not None and found.name == "odoo-bin"


def test_require_odoo_project_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Not an Odoo project"):
        require_odoo_project(tmp_path)


def test_require_odoo_project_returns_bin_path(tmp_path: Path) -> None:
    bin_path = tmp_path / "odoo-bin"
    bin_path.write_text("#!/usr/bin/env python\n")
    assert require_odoo_project(tmp_path) == bin_path
