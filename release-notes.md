# Release Notes

## 0.1.0 (Unreleased)

First release. A Rich-powered CLI for everyday Odoo development tasks — manage modules, scaffold code, run the server, and handle crons without writing ORM scripts in `odoo shell`.

### Commands

- **Server**: `run` — launches `odoo-bin` with cfg + db from `odoo.conf`. Extra flags pass through (e.g. `orc run --dev all -u sale -- --workers=0`).
- **Modules**: `install`, `upgrade`, `uninstall`, `update-list`, `info`, `list`.
- **Databases**: `db list`, `db backup`, `db restore`, `db duplicate`, `db drop` — wraps Odoo's own `service.db` functions; refuses to drop the connected DB.
- **Maintenance**: `clear-assets`, `reset-password`.
- **Crons**: `cron-list`, `cron-toggle`, `cron-on`, `cron-off`.
- **Development**: `scaffold` (module skeleton generator), `shell-exec` (run an arbitrary `.py` through `odoo shell`).

### Interactive menu

- Run `orc` with no arguments for a Rich UI organised into managers — Module / Database / Asset / User / Cron / Dev Tools — each with its own sub-menu. `Run` is a top-level direct action.
- ASCII banner, "Connected" config status panel, sensible Ctrl+C handling.

### CLI ergonomics

- Short command name: `orc`. The full `odoo-rich-cli` is also installed as an alias, so `uvx odoo-rich-cli` works without `--from`.
- Global `-c` / `-d` flags work at the top level and on every subcommand.
- Embed helper: `from odoo_rich_cli import run` lets you drop a `cli.py` in your project root and pre-configure defaults.

### Project-aware behaviour

- Requires an `odoo-bin` file in the current directory; exits with a clear error otherwise.
- `odoo-bin` is invoked under `$VIRTUAL_ENV/python` when an odoo venv is activated, falling back to `sys.executable`. Makes `uv tool install` / `uvx` cooperate with the user's odoo venv.
- Database is required: orc fails fast if neither `db_name` in `odoo.conf` nor `-d` is provided.
- Wrapped scripts preflight `env` and surface "No database loaded" instead of a confusing `NameError`.

### Packaging & typing

- Source layout: `src/odoo_rich_cli/`.
- Fully typed (`py.typed` ships in the wheel; `mypy strict = true` passes clean).
- Python 3.10+. Dependencies: `rich >= 13.0.0`, `typer >= 0.9.0`.
- Hatchling build backend; version is read dynamically from `__init__.py`.

### Dev tooling

- Ruff + mypy configured via `[dependency-groups]`. Run with `uv run ruff check`, `uv run mypy`.
- Dependabot configured for `uv` and `github-actions` ecosystems, weekly.
