import configparser
from dataclasses import dataclass
from pathlib import Path

ODOO_BIN = "odoo-bin"
ODOO_CONF = "odoo.conf"


@dataclass
class OdooConfig:
    db_name: str
    addons_path: str
    config_path: Path

    @property
    def config_path_str(self) -> str:
        return str(self.config_path)


def find_odoo_bin(path: Path | None = None) -> Path | None:
    candidate = (path or Path.cwd()) / ODOO_BIN
    return candidate if candidate.is_file() else None


def require_odoo_project(path: Path | None = None) -> Path:
    base = path or Path.cwd()
    bin_path = find_odoo_bin(base)
    if bin_path is None:
        raise FileNotFoundError(
            f"Not an Odoo project: no '{ODOO_BIN}' in {base}. "
            "Run orc from the root of an Odoo project."
        )
    return bin_path


def find_config(path: Path | None = None) -> Path:
    conf = (path or Path.cwd()) / ODOO_CONF
    if conf.is_file():
        return conf
    raise FileNotFoundError(
        f"No {ODOO_CONF} found in {conf.parent}. "
        f"Run from a directory containing {ODOO_CONF}, or pass --config."
    )


def parse_config(path: Path) -> OdooConfig:
    parser = configparser.ConfigParser()
    parser.read(path)

    db_name = parser.get("options", "db_name", fallback="")
    # Odoo writes "False" as the default for unset values
    if db_name in ("False", "false", "None", "none"):
        db_name = ""

    return OdooConfig(
        db_name=db_name,
        addons_path=parser.get("options", "addons_path", fallback=""),
        config_path=path,
    )


def resolve_config(
    config_path: str | None = None,
    database: str | None = None,
) -> OdooConfig:
    path = Path(config_path) if config_path else find_config()
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    config = parse_config(path)
    if database:
        config.db_name = database

    if not config.db_name:
        raise ValueError("No database specified. Set db_name in odoo.conf or pass -d <database>.")

    return config
