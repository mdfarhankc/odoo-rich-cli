from pathlib import Path

import pytest

from odoo_rich_cli.scaffold import _class_name, create_module


def test_creates_expected_layout(tmp_path: Path) -> None:
    created = create_module("my_module", str(tmp_path))
    base = Path(created)

    assert base == tmp_path / "my_module"
    for relpath in [
        "__manifest__.py",
        "__init__.py",
        "models/__init__.py",
        "models/models.py",
        "views/views.xml",
        "security/ir.model.access.csv",
        "controllers/__init__.py",
        "controllers/controllers.py",
        "static/description/.gitkeep",
    ]:
        assert (base / relpath).is_file(), f"missing: {relpath}"


def test_manifest_contains_module_name(tmp_path: Path) -> None:
    create_module("sale_extension", str(tmp_path))
    manifest = (tmp_path / "sale_extension" / "__manifest__.py").read_text()
    assert '"name": "sale_extension"' in manifest


def test_models_py_uses_dotted_model_name(tmp_path: Path) -> None:
    create_module("my_module", str(tmp_path))
    models = (tmp_path / "my_module" / "models" / "models.py").read_text()
    assert '_name = "my.module"' in models
    assert "class MyModule(models.Model):" in models


def test_refuses_to_overwrite_existing(tmp_path: Path) -> None:
    create_module("foo", str(tmp_path))
    with pytest.raises(FileExistsError):
        create_module("foo", str(tmp_path))


def test_class_name_camelcases_underscores() -> None:
    assert _class_name("my_module") == "MyModule"
    assert _class_name("a_b_c") == "ABC"
    assert _class_name("single") == "Single"
