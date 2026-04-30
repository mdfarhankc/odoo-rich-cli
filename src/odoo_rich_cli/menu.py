from collections.abc import Callable
from pathlib import Path

import typer
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from odoo_rich_cli import __version__, commands, shell, ui
from odoo_rich_cli.config import OdooConfig, resolve_config
from odoo_rich_cli.scaffold import create_module
from odoo_rich_cli.shell import ShellResult
from odoo_rich_cli.ui import console

# Action callables have varying signatures (some take cfg only, others cfg + module
# / cron_id / state filter), so the registry types them as Callable[..., R].
ActionFn = Callable[..., ShellResult]
Action = tuple[str, str, str, ActionFn | None, str, str]
TopEntry = tuple[str, str, str, str, str | list[Action]]


BANNER = r"""
   ____     __               ________    ____
  / __ \___/ /___  ___      / ___/ /    /  _/
 / /_/ / _  / __ \/ __ \   / /  / /    _/ /
 \____/\_,_/\____/\____/  /___/_/____/___/
"""


MODULE_ACTIONS: list[Action] = [
    ("1", "Install",     "Install a module",               commands.install_module,   "Installing",      "module"),
    ("2", "Upgrade",     "Upgrade an installed module",    commands.upgrade_module,   "Upgrading",       "module"),
    ("3", "Uninstall",   "Remove an installed module",     commands.uninstall_module, "Uninstalling",    "module"),
    ("4", "Update List", "Refresh available modules list", commands.update_list,      "Updating list",   "none"),
    ("5", "Info",        "Show details about a module",    commands.module_info,      "Fetching info",   "module"),
    ("6", "List",        "List modules by state",          commands.list_modules,     "Listing modules", "list_filter"),
]  # fmt: skip

ASSET_ACTIONS: list[Action] = [
    (
        "1",
        "Clear Assets",
        "Delete compiled CSS/JS bundles",
        commands.clear_assets,
        "Clearing assets",
        "none",
    ),
]

USER_ACTIONS: list[Action] = [
    (
        "1",
        "Reset Password",
        "Reset a user's password",
        commands.reset_password,
        "Resetting",
        "password",
    ),
]

CRON_ACTIONS: list[Action] = [
    ("1", "List",        "List all scheduled actions", commands.cron_list,        "Listing crons",       "cron_list"),
    ("2", "Toggle",      "Toggle a cron by ID",        commands.cron_toggle,      "Toggling cron",       "cron_toggle"),
    ("3", "Disable All", "Disable every cron",         commands.cron_disable_all, "Disabling all crons", "none"),
    ("4", "Enable All",  "Enable every cron",          commands.cron_enable_all,  "Enabling all crons",  "none"),
]  # fmt: skip

DEV_ACTIONS: list[Action] = [
    ("1", "Scaffold", "Generate a new module skeleton", None, "", "scaffold"),
    ("2", "Shell Exec", "Run a Python script via shell", None, "", "shell_exec"),
]

DB_ACTIONS: list[Action] = [
    ("1", "List",      "List databases on the server",  commands.db_list, "Listing databases", "db_list"),
    ("2", "Backup",    "Back up a database to zip",     None,             "Backing up",        "db_backup"),
    ("3", "Restore",   "Restore a database from zip",   None,             "Restoring",         "db_restore"),
    ("4", "Duplicate", "Duplicate a database",          None,             "Duplicating",       "db_duplicate"),
    ("5", "Drop",      "Delete a database (confirm)",   None,             "Dropping",          "db_drop"),
]  # fmt: skip


TOP_MENU: list[TopEntry] = [
    ("1", "Run",              "Launch the Odoo server",                "direct",  "run"),
    ("2", "Module Manager",   "Install / upgrade / info / list",       "manager", MODULE_ACTIONS),
    ("3", "Database Manager", "List / backup / restore / drop",        "manager", DB_ACTIONS),
    ("4", "Asset Manager",    "Clear compiled asset bundles",          "manager", ASSET_ACTIONS),
    ("5", "User Manager",     "Reset passwords",                       "manager", USER_ACTIONS),
    ("6", "Cron Manager",     "List, toggle, enable/disable crons",    "manager", CRON_ACTIONS),
    ("7", "Dev Tools",        "Scaffold a module / run shell scripts", "manager", DEV_ACTIONS),
]  # fmt: skip


def _show_header() -> None:
    console.print(
        Panel(
            Text(BANNER, style="bold purple"),
            subtitle=f"[dim]v{__version__}[/]",
            border_style="bright_blue",
            padding=(0, 2),
        )
    )


def _show_config_status(config_path: str | None, database: str | None) -> OdooConfig | None:
    try:
        cfg = resolve_config(config_path, database)
    except (FileNotFoundError, ValueError) as e:
        console.print(
            Panel(
                f"[yellow]{e}[/]",
                title="[bold yellow]No Config[/]",
                border_style="yellow",
                padding=(0, 2),
            )
        )
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="dim", width=10)
    table.add_column(style="bold")
    table.add_row("Config", str(cfg.config_path))
    table.add_row("Database", cfg.db_name)
    console.print(
        Panel(table, title="[bold green]Connected[/]", border_style="green", padding=(0, 2))
    )
    return cfg


def _menu_panel(title: str, rows: list[tuple[str, str, str]], footer: tuple[str, str, str]) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=6, justify="center")
    table.add_column(style="bold white", width=18)
    table.add_column(style="dim")

    for key, name, desc in rows:
        table.add_row(f"[{key}]", name, desc)
    table.add_row("")
    table.add_row(f"[{footer[0]}]", footer[1], footer[2])

    console.print(
        Panel(table, title=f"[bold]{title}[/]", border_style="bright_blue", padding=(1, 2))
    )


def _show_top_menu() -> None:
    rows = [(k, n, d) for k, n, d, *_ in TOP_MENU]
    _menu_panel("Operations", rows, ("0", "Exit", "Quit the CLI"))


def _show_submenu(title: str, actions: list[Action]) -> None:
    rows = [(k, n, d) for k, n, d, *_ in actions]
    _menu_panel(title, rows, ("0", "Back", "Return to main menu"))


def _get_config(
    cached_cfg: OdooConfig | None,
    config_path: str | None,
    database: str | None,
) -> OdooConfig:
    if cached_cfg is not None:
        return cached_cfg
    cp = console.input("  [bold]Config path[/] [dim](Enter for ./odoo.conf):[/] ").strip() or None
    db = console.input("  [bold]Database:[/] ").strip() or None
    return resolve_config(cp, db)


def _handle_module(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    module = console.input("  [bold]Module name:[/] ").strip()
    if not module:
        console.print("  [red]Module name cannot be empty.[/]")
        return

    console.print()
    with ui.status(action_label, cfg.db_name, target=module):
        result = action_fn(cfg, module)

    if action_fn is commands.module_info and result.success and result.data:
        ui.render_module_info(result.data)
    else:
        ui.show_result(result)


def _handle_simple(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    console.print()
    with ui.status(action_label, cfg.db_name):
        result = action_fn(cfg)
    ui.show_result(result)


def _handle_list_filter(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    console.print("  [bold]Filter:[/] [dim](1) All  (2) Installed  (3) Uninstalled[/]")
    choice = console.input("  [bold bright_blue]>[/] ").strip()
    state_filter = {"1": "all", "2": "installed", "3": "uninstalled"}.get(choice, "all")

    console.print()
    with ui.status(action_label, cfg.db_name):
        result = action_fn(cfg, state_filter)

    if result.success and result.data:
        ui.render_module_list(result.data, result.message)
    else:
        ui.show_result(result)


def _handle_password(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    user = console.input("  [bold]User login[/] [dim](Enter for admin):[/] ").strip() or "admin"
    pw = console.input("  [bold]New password[/] [dim](Enter for admin):[/] ").strip() or "admin"

    console.print()
    with ui.status("Resetting password for", cfg.db_name, target=user):
        result = action_fn(cfg, user, pw)
    ui.show_result(result)


def _handle_cron_list(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    console.print()
    with ui.status(action_label, cfg.db_name):
        result = action_fn(cfg)
    if result.success and result.data:
        ui.render_cron_list(result.data, result.message)
    else:
        ui.show_result(result)


def _handle_cron_toggle(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    cron_id_str = console.input("  [bold]Cron ID:[/] ").strip()
    if not cron_id_str.isdigit():
        console.print("  [red]Invalid ID. Must be a number.[/]")
        return
    console.print()
    with ui.status(action_label, cfg.db_name, target=f"#{cron_id_str}"):
        result = action_fn(cfg, int(cron_id_str))
    ui.show_result(result)


def _handle_scaffold(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    module = console.input("  [bold]Module name:[/] ").strip()
    if not module:
        console.print("  [red]Module name cannot be empty.[/]")
        return
    path = console.input("  [bold]Path[/] [dim](Enter for current dir):[/] ").strip() or "."

    try:
        created = create_module(module, path)
    except FileExistsError as e:
        ui.show_failure(str(e))
        return

    ui.show_success(f"Module created at [bold]{created}[/]", title="Scaffolded")


def _handle_shell_exec(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    file = console.input("  [bold]Script path:[/] ").strip()
    script_path = Path(file)
    if not script_path.is_file():
        ui.show_failure(f"File not found: {file}")
        return

    console.print()
    with ui.status("Running", cfg.db_name, target=script_path.name):
        result = commands.shell_exec(cfg, script_path.read_text(encoding="utf-8"))
    ui.show_result(result)


def _handle_db_list(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    assert action_fn is not None
    console.print()
    with ui.status(action_label, cfg.db_name):
        result = action_fn(cfg)
    if result.success and result.data:
        ui.render_db_list(result.data, result.message)
    else:
        ui.show_result(result)


def _handle_db_backup(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    name = console.input("  [bold]Database name:[/] ").strip()
    if not name:
        console.print("  [red]Database name cannot be empty.[/]")
        return
    output = console.input(
        "  [bold]Output path[/] [dim](Enter for ./<db>-<timestamp>.zip):[/] "
    ).strip()
    if not output:
        from datetime import datetime

        output = f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"

    console.print()
    with ui.status(action_label, cfg.db_name, target=name):
        result = commands.db_backup(cfg, name, str(Path(output).resolve()))
    ui.show_result(result)


def _handle_db_restore(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    name = console.input("  [bold]Target database name:[/] ").strip()
    if not name:
        console.print("  [red]Database name cannot be empty.[/]")
        return
    src = console.input("  [bold]Backup file path:[/] ").strip()
    if not Path(src).is_file():
        ui.show_failure(f"File not found: {src}")
        return

    console.print()
    with ui.status(action_label, cfg.db_name, target=name):
        result = commands.db_restore(cfg, name, str(Path(src).resolve()))
    ui.show_result(result)


def _handle_db_duplicate(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    source = console.input("  [bold]Source database:[/] ").strip()
    target = console.input("  [bold]New database name:[/] ").strip()
    if not source or not target:
        console.print("  [red]Source and target are required.[/]")
        return

    console.print()
    with ui.status(action_label, cfg.db_name, target=f"{source} → {target}"):
        result = commands.db_duplicate(cfg, source, target)
    ui.show_result(result)


def _handle_db_drop(cfg: OdooConfig, action_fn: ActionFn | None, action_label: str) -> None:
    name = console.input("  [bold]Database to drop:[/] ").strip()
    if not name:
        console.print("  [red]Database name cannot be empty.[/]")
        return
    confirm = console.input(f"  [red]Type '{name}' to confirm: [/]").strip()
    if confirm != name:
        console.print("  [yellow]Cancelled.[/]")
        return

    console.print()
    with ui.status(action_label, cfg.db_name, target=name):
        result = commands.db_drop(cfg, name)
    ui.show_result(result)


HANDLERS = {
    "module":       _handle_module,
    "none":         _handle_simple,
    "list_filter":  _handle_list_filter,
    "password":     _handle_password,
    "cron_list":    _handle_cron_list,
    "cron_toggle":  _handle_cron_toggle,
    "scaffold":     _handle_scaffold,
    "shell_exec":   _handle_shell_exec,
    "db_list":      _handle_db_list,
    "db_backup":    _handle_db_backup,
    "db_restore":   _handle_db_restore,
    "db_duplicate": _handle_db_duplicate,
    "db_drop":      _handle_db_drop,
}  # fmt: skip


def _run_server(cfg: OdooConfig) -> None:
    console.print()
    console.print("[dim]  Starting Odoo server. Press Ctrl+C to stop.[/]")
    console.print()
    code = shell.run_server(cfg.config_path_str, cfg.db_name)
    if code not in (0, 130):
        ui.show_failure(f"odoo-bin exited with code {code}")


DIRECT_ACTIONS = {"run": _run_server}


def _run_manager(cfg: OdooConfig, title: str, actions: list[Action]) -> None:
    action_map = {a[0]: a for a in actions}

    while True:
        console.print()
        _show_submenu(title, actions)
        choice = console.input("\n  [bold bright_blue]>[/] ").strip()

        if choice == "0":
            return
        if choice not in action_map:
            console.print("  [red]Invalid choice.[/]")
            continue

        _, _, _, action_fn, action_label, prompt_type = action_map[choice]
        console.print()
        console.print(Rule(style="dim"))
        HANDLERS[prompt_type](cfg, action_fn, action_label)


def interactive_menu(config_path: str | None = None, database: str | None = None) -> None:
    console.clear()
    _show_header()

    cached_cfg = _show_config_status(config_path, database)
    top_map = {entry[0]: entry for entry in TOP_MENU}

    while True:
        console.print()
        _show_top_menu()

        choice = console.input("\n  [bold bright_blue]>[/] ").strip()

        if choice == "0":
            console.print()
            console.print(Rule("[dim]Goodbye[/]", style="dim"))
            console.print()
            raise typer.Exit()

        if choice not in top_map:
            console.print("  [red]Invalid choice.[/]")
            continue

        _, name, _, _kind, payload = top_map[choice]
        console.print()
        console.print(Rule(style="dim"))

        try:
            cfg = _get_config(cached_cfg, config_path, database)
        except (FileNotFoundError, ValueError) as e:
            ui.show_failure(str(e))
            continue

        if isinstance(payload, str):
            DIRECT_ACTIONS[payload](cfg)
        else:
            _run_manager(cfg, name, payload)
