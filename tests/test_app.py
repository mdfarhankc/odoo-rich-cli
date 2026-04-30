import sys
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from odoo_rich_cli.app import _has_flag, run


@pytest.fixture
def fake_argv() -> Iterator[list[str]]:
    """Replace sys.argv with a controllable list and restore afterwards."""
    original = sys.argv[:]
    sys.argv[:] = ["cli.py"]
    try:
        yield sys.argv
    finally:
        sys.argv[:] = original


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["-c", "x"], True),
        (["--config", "x"], True),
        (["--config=x"], True),
        (["other"], False),
        (["--configuration"], False),
        ([], False),
    ],
)
def test_has_flag_recognises_short_long_and_equals(argv: list[str], expected: bool) -> None:
    assert _has_flag(argv, "-c", "--config") is expected


def test_run_injects_defaults_when_argv_omits_them(fake_argv: list[str]) -> None:
    fake_argv.extend(["install", "-m", "sale"])

    with patch("odoo_rich_cli.app.app") as mock_app:
        run(config="custom.conf", database="my_db")

    assert sys.argv == ["cli.py", "-c", "custom.conf", "-d", "my_db", "install", "-m", "sale"]
    mock_app.assert_called_once()


def test_run_skips_injection_when_argv_already_has_flag(fake_argv: list[str]) -> None:
    fake_argv.extend(["-d", "explicit", "list"])

    with patch("odoo_rich_cli.app.app") as mock_app:
        run(config="custom.conf", database="my_db")

    # -c is injected, -d is left alone because the user passed it
    assert sys.argv == ["cli.py", "-c", "custom.conf", "-d", "explicit", "list"]
    mock_app.assert_called_once()


def test_run_with_no_defaults_passes_argv_through(fake_argv: list[str]) -> None:
    fake_argv.extend(["list", "--installed"])

    with patch("odoo_rich_cli.app.app") as mock_app:
        run()

    assert sys.argv == ["cli.py", "list", "--installed"]
    mock_app.assert_called_once()
