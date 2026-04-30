# Odoo Rich CLI

A Rich-powered CLI for everyday Odoo development tasks — run the server, manage modules, scaffold code, and handle crons without writing ORM scripts in `odoo shell`.

Compatible with **Odoo 14+** and **Python 3.10+**.

The CLI command is **`orc`** (Odoo Rich Cli). Install it once globally and run it from any Odoo project root.

## Features

- **20 commands** — run, install, upgrade, uninstall, update-list, info, list, clear-assets, reset-password, scaffold, shell-exec, cron-list, cron-toggle, cron-on, cron-off, plus a `db` group: `db list`, `db backup`, `db restore`, `db duplicate`, `db drop`
- **Interactive menu** — run `orc` with no arguments for a guided Rich UI organised into managers (Module / Database / Asset / User / Cron / Dev Tools)
- **Global flags** — pass `-c` and `-d` at the top level, works for both direct commands and interactive mode
- **Project-aware** — `orc` only runs inside an Odoo project root (detected by an `odoo-bin` file). It runs `odoo-bin` with the active virtualenv's Python (or `sys.executable` as a fallback)
- **Reads odoo.conf** — auto-detects database and config from your project directory

## Installation

```bash
pip install odoo-rich-cli
```

Or with [pipx](https://pipx.pypa.io/) / [uv](https://github.com/astral-sh/uv) for an isolated global install:

```bash
pipx install odoo-rich-cli
# or
uv tool install odoo-rich-cli
```

Both expose the `orc` command on PATH.

### Run without installing

```bash
uvx odoo-rich-cli
```

`uvx` (`uv tool run`) downloads the package into a temporary environment and invokes it. Use the full `odoo-rich-cli` name here; the short `orc` only works once installed.

### Embed in your project

If you'd rather not install anything globally, drop a `cli.py` in your Odoo project root and call the embed helper. Defaults you pass are pre-applied; the user can still override them on the command line.

```python
# cli.py
from odoo_rich_cli import run

if __name__ == "__main__":
    run(config="./config/odoo.conf", database="my_db")
```

```bash
python cli.py install -m sale       # runs with the baked-in -c/-d defaults
python cli.py -d other_db list      # override database for one call
python cli.py                       # launch the interactive menu
```

This still requires `odoo-rich-cli` to be installed in your venv (e.g. `pip install odoo-rich-cli` alongside Odoo) — it just spares you from typing `orc -c … -d …` every time.

## Commands

| Command | Description |
|---|---|
| `run` | Launch the Odoo server (extra flags pass through to odoo-bin) |
| `install -m <module>` | Install a module |
| `upgrade -m <module>` | Upgrade an installed module |
| `uninstall -m <module>` | Uninstall a module |
| `update-list` | Refresh the list of available modules |
| `info -m <module>` | Show module details (state, version, dependencies, dependents) |
| `list` | List modules (with `--installed` or `--uninstalled` filter) |
| `clear-assets` | Delete compiled CSS/JS asset bundles |
| `reset-password` | Reset a user's password (default: admin/admin) |
| `scaffold -m <module>` | Generate a new module skeleton |
| `shell-exec -f <script.py>` | Run an arbitrary Python script through odoo shell |
| `cron-list` | List all scheduled actions with their status |
| `cron-toggle -i <id>` | Toggle a single scheduled action on/off |
| `cron-on` | Enable ALL scheduled actions |
| `cron-off` | Disable ALL scheduled actions |
| `db list` | List databases on the configured PostgreSQL server |
| `db backup <name> [-o file.zip]` | Back up a database to a zip file |
| `db restore <name> -i file.zip [--copy]` | Restore a database from a zip backup |
| `db duplicate <source> <target>` | Duplicate a database |
| `db drop <name> [-y]` | Drop a database (interactive confirmation by default) |

## Usage

Run `orc` from your Odoo project directory (where `odoo-bin` lives), with your Odoo virtualenv activated. If `odoo-bin` is not in the current directory, `orc` will exit with an error.

### Run the Odoo server

```bash
orc run                                # uses cfg + db from odoo.conf
orc run --dev all -u sale              # any odoo-bin flags pass through
orc run -- --workers=0 --log-level=debug  # use `--` for flags ambiguous with orc's own
```

stdout/stderr stream live; press Ctrl+C to stop the server.

### Module operations

```bash
orc install -m sale
orc upgrade -m sale
orc uninstall -m sale
```

### Module discovery

```bash
# Refresh module list (required before installing new modules)
orc update-list

# Show details about a module
orc info -m sale

# List all installed modules
orc list --installed

# List all modules
orc list
```

### Maintenance

```bash
# Clear compiled CSS/JS assets (fixes "my styles aren't updating")
orc clear-assets

# Reset admin password to "admin"
orc reset-password

# Reset a specific user's password
orc reset-password -u john -p newpass123
```

### Cron management

```bash
# List all scheduled actions
orc cron-list

# Toggle a specific cron by ID
orc cron-toggle -i 42

# Disable every scheduled action (useful for staging restores)
orc cron-off

# Re-enable every scheduled action
orc cron-on
```

### Database operations

```bash
# List databases on the server
orc db list

# Back up a database (default output: <name>-<timestamp>.zip in cwd)
orc db backup my_db
orc db backup my_db -o /backups/snapshot.zip

# Restore from a zip
orc db restore new_db -i /backups/snapshot.zip
orc db restore new_db -i /backups/snapshot.zip --copy   # resets UUID + crons

# Duplicate
orc db duplicate prod_clone staging

# Drop (asks for confirmation; -y to skip)
orc db drop scratch_db
orc db drop scratch_db -y
```

`orc db` shells into the configured working DB and operates on the target as an
argument, so dropping the connected DB is refused — use `-d` to point at a
different database first if you need to.

### Development

```bash
# Generate a new module skeleton
orc scaffold -m my_custom_module

# Generate in a specific directory
orc scaffold -m my_custom_module -p ./addons

# Run a custom script through odoo shell
orc shell-exec -f fix_data.py
```

### Global flags

The `-c` (config) and `-d` (database) flags work at the top level and on every subcommand:

```bash
# Launch interactive menu with a specific config
orc -c ./local-odoo.conf

# Direct command with config and database override
orc install -m sale -c /path/to/odoo.conf -d my_database
```

### Interactive menu

```bash
orc
```

Launches a Rich interactive menu with an ASCII banner, config status panel, and a numbered top-level menu:

```
[1] Run               Launch the Odoo server
[2] Module Manager    Install / upgrade / info / list
[3] Database Manager  List / backup / restore / drop
[4] Asset Manager     Clear compiled asset bundles
[5] User Manager      Reset passwords
[6] Cron Manager      List, toggle, enable/disable crons
[7] Dev Tools         Scaffold a module / run shell scripts
[0] Exit
```

Each manager opens a sub-menu with `[0] Back`. If config was auto-detected, you won't be prompted for it again.

## How it works

1. `orc` requires an `odoo-bin` file in the current directory — that's the marker for "this is an Odoo project". If missing, it exits with a clear error.
2. It runs `./odoo-bin` using your currently active Python interpreter (`sys.executable`), so the call uses the venv you activated.
3. For shell-based commands it builds a Python ORM script and pipes it into `odoo shell -c <conf> -d <db> --no-http` via subprocess.
4. Each script runs the operation and calls `env.cr.commit()` so changes persist after the shell exits.
5. Output is parsed via a sentinel marker for reliable result extraction from odoo shell's startup noise.

## Testing locally

### Prerequisites

- An Odoo source checkout with `odoo-bin` in the project root
- A PostgreSQL database already set up
- An `odoo.conf` file in the project root
- Your Odoo virtualenv activated (so all dependencies are available)

### Install in editable mode

Install `orc` into your Odoo virtualenv so everything shares the same environment:

```bash
pip install -e .
```

With editable mode (`-e`), code changes are picked up immediately — no need to reinstall after every edit.

### Test commands

```bash
# Verify the CLI loads
orc --help

# Test interactive menu
orc

# Test against your database
orc update-list
orc list --installed
orc info -m sale
orc install -m sale
orc upgrade -m sale
orc clear-assets
orc reset-password
orc scaffold -m test_module -p /tmp
orc cron-list
```

## Project structure

```
odoo-rich-cli/
├── pyproject.toml              # Project metadata, dependencies, entry point (orc)
├── main.py                     # Thin entry point: python main.py
├── src/
│   └── odoo_rich_cli/
│       ├── __init__.py         # Package version + run() embed helper export
│       ├── config.py           # odoo.conf parsing + odoo-bin / project-root detection
│       ├── shell.py            # Pipes scripts into odoo shell, runs odoo server, parses sentinel output
│       ├── commands.py         # ORM scripts for all shell-based commands
│       ├── scaffold.py         # Module skeleton generator (pure file creation)
│       ├── ui.py               # Shared Rich panels, tables, and status spinner
│       ├── app.py              # Typer CLI app with all commands
│       └── menu.py             # Rich interactive menu (managers + sub-menus)
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up the dev environment, submitting PRs, and reporting bugs.

## License

MIT — see [LICENSE](LICENSE) for details.
