import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Annotated

import typer

from odoo_rich_cli import commands, shell, ui
from odoo_rich_cli.config import OdooConfig, require_odoo_project, resolve_config
from odoo_rich_cli.shell import ShellResult

app = typer.Typer(
    name="orc",
    help="A Rich-powered CLI for everyday Odoo development tasks.",
    no_args_is_help=False,
)

ConfigOpt = Annotated[
    str | None,
    typer.Option("--config", "-c", help="Path to odoo.conf (default: ./odoo.conf)."),
]
DatabaseOpt = Annotated[
    str | None,
    typer.Option("--database", "-d", help="Database name (overrides odoo.conf)."),
]
ModuleOpt = Annotated[str, typer.Option("--module", "-m", help="Technical name of the module.")]


def _resolve_or_exit(config_path: str | None, database: str | None) -> OdooConfig:
    try:
        require_odoo_project()
        return resolve_config(config_path, database)
    except (FileNotFoundError, ValueError) as e:
        ui.exit_with_error(str(e))


def _run_with_module(
    label: str,
    action_fn: Callable[[OdooConfig, str], ShellResult],
    module: str,
    config_path: str | None,
    database: str | None,
) -> None:
    cfg = _resolve_or_exit(config_path, database)
    with ui.status(label, cfg.db_name, target=module):
        result = action_fn(cfg, module)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


def _run_simple(
    label: str,
    action_fn: Callable[[OdooConfig], ShellResult],
    config_path: str | None,
    database: str | None,
) -> None:
    cfg = _resolve_or_exit(config_path, database)
    with ui.status(label, cfg.db_name):
        result = action_fn(cfg)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@app.command()
def install(module: ModuleOpt, config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Install an Odoo module."""
    _run_with_module("Installing", commands.install_module, module, config, database)


@app.command()
def upgrade(module: ModuleOpt, config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Upgrade an installed Odoo module."""
    _run_with_module("Upgrading", commands.upgrade_module, module, config, database)


@app.command()
def uninstall(module: ModuleOpt, config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Uninstall an Odoo module."""
    _run_with_module("Uninstalling", commands.uninstall_module, module, config, database)


@app.command("update-list")
def update_list(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Refresh the list of available modules."""
    _run_simple("Updating module list", commands.update_list, config, database)


@app.command()
def info(module: ModuleOpt, config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Show details about a module."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Fetching info", cfg.db_name, target=module):
        result = commands.module_info(cfg, module)

    if not result.success:
        ui.exit_with_error(result.message)
    ui.render_module_info(result.data)


@app.command("list")
def list_cmd(
    installed: Annotated[bool, typer.Option("--installed", help="Only installed modules.")] = False,
    uninstalled: Annotated[
        bool, typer.Option("--uninstalled", help="Only uninstalled modules.")
    ] = False,
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """List modules, optionally filtered by state."""
    state_filter = "installed" if installed else "uninstalled" if uninstalled else "all"

    cfg = _resolve_or_exit(config, database)
    with ui.status("Listing modules", cfg.db_name):
        result = commands.list_modules(cfg, state_filter)

    if not result.success:
        ui.exit_with_error(result.message)
    ui.render_module_list(result.data, result.message)


@app.command("clear-assets")
def clear_assets(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Delete compiled CSS/JS asset bundles."""
    _run_simple("Clearing assets", commands.clear_assets, config, database)


@app.command("reset-password")
def reset_password(
    user: Annotated[str, typer.Option("--user", "-u", help="User login.")] = "admin",
    password: Annotated[str, typer.Option("--password", "-p", help="New password.")] = "admin",
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Reset a user's password (default: admin/admin)."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Resetting password for", cfg.db_name, target=user):
        result = commands.reset_password(cfg, user, password)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@app.command("shell-exec")
def shell_exec(
    file: Annotated[str, typer.Option("--file", "-f", help="Path to a .py file to execute.")],
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Run an arbitrary Python script through odoo shell."""
    script_path = Path(file)
    if not script_path.is_file():
        ui.exit_with_error(f"File not found: {file}")

    cfg = _resolve_or_exit(config, database)
    with ui.status("Running", cfg.db_name, target=script_path.name):
        result = commands.shell_exec(cfg, script_path.read_text(encoding="utf-8"))
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@app.command()
def scaffold(
    module: ModuleOpt,
    path: Annotated[str, typer.Option("--path", "-p", help="Where to create it.")] = ".",
) -> None:
    """Generate a new Odoo module skeleton."""
    from odoo_rich_cli.scaffold import create_module

    try:
        require_odoo_project()
        created_path = create_module(module, path)
    except (FileNotFoundError, FileExistsError) as e:
        ui.exit_with_error(str(e))

    ui.show_success(f"Module created at [bold]{created_path}[/]", title="Scaffolded")


@app.command(
    name="run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_odoo(
    ctx: typer.Context,
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Launch the Odoo server. Extra flags pass through to odoo-bin.

    Example: orc run --dev all -u sale -- --workers=0
    """
    cfg = _resolve_or_exit(config, database)
    code = shell.run_server(cfg.config_path_str, cfg.db_name, ctx.args)
    if code != 0:
        raise typer.Exit(code)


@app.command("cron-list")
def cron_list(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """List all scheduled actions with their status."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Listing crons", cfg.db_name):
        result = commands.cron_list(cfg)

    if not result.success:
        ui.exit_with_error(result.message)
    ui.render_cron_list(result.data, result.message)


@app.command("cron-toggle")
def cron_toggle(
    cron_id: Annotated[int, typer.Option("--id", "-i", help="Scheduled action ID.")],
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Toggle a scheduled action on/off."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Toggling cron", cfg.db_name, target=f"#{cron_id}"):
        result = commands.cron_toggle(cfg, cron_id)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@app.command("cron-off")
def cron_off(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Disable every scheduled action."""
    _run_simple("Disabling all crons", commands.cron_disable_all, config, database)


@app.command("cron-on")
def cron_on(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Enable every scheduled action."""
    _run_simple("Enabling all crons", commands.cron_enable_all, config, database)


db_app = typer.Typer(help="Database operations (list, backup, restore, duplicate, drop).")
app.add_typer(db_app, name="db")


def _default_backup_path(db_name: str) -> str:
    from datetime import datetime

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{db_name}-{stamp}.zip"


@db_app.command("list")
def db_list(config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """List databases on the configured PostgreSQL server."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Listing databases", cfg.db_name):
        result = commands.db_list(cfg)

    if not result.success:
        ui.exit_with_error(result.message)
    ui.render_db_list(result.data, result.message)


@db_app.command("backup")
def db_backup(
    name: Annotated[str, typer.Argument(help="Database to back up.")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output zip path.")] = None,
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Back up a database to a zip file."""
    cfg = _resolve_or_exit(config, database)
    output_path = str(Path(output).resolve()) if output else _default_backup_path(name)

    with ui.status("Backing up", cfg.db_name, target=name):
        result = commands.db_backup(cfg, name, output_path)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@db_app.command("restore")
def db_restore(
    name: Annotated[str, typer.Argument(help="Target database name.")],
    input: Annotated[str, typer.Option("--input", "-i", help="Path to backup zip.")],
    copy: Annotated[
        bool, typer.Option("--copy", help="Restore as a copy (resets UUID, disables crons).")
    ] = False,
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Restore a database from a backup zip."""
    src = Path(input)
    if not src.is_file():
        ui.exit_with_error(f"Backup file not found: {input}")

    cfg = _resolve_or_exit(config, database)
    with ui.status("Restoring", cfg.db_name, target=name):
        result = commands.db_restore(cfg, name, str(src.resolve()), copy)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@db_app.command("duplicate")
def db_duplicate(
    source: Annotated[str, typer.Argument(help="Source database.")],
    target: Annotated[str, typer.Argument(help="New database name.")],
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Duplicate a database."""
    cfg = _resolve_or_exit(config, database)
    with ui.status("Duplicating", cfg.db_name, target=f"{source} → {target}"):
        result = commands.db_duplicate(cfg, source, target)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@db_app.command("drop")
def db_drop(
    name: Annotated[str, typer.Argument(help="Database to drop.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
    config: ConfigOpt = None,
    database: DatabaseOpt = None,
) -> None:
    """Drop a database. Asks for confirmation unless --yes is passed."""
    if not yes and not typer.confirm(f"Drop database '{name}'? This cannot be undone."):
        raise typer.Exit()

    cfg = _resolve_or_exit(config, database)
    with ui.status("Dropping", cfg.db_name, target=name):
        result = commands.db_drop(cfg, name)
    ui.show_result(result)
    if not result.success:
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, config: ConfigOpt = None, database: DatabaseOpt = None) -> None:
    """Launch the interactive menu if no command is given."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["database"] = database

    if ctx.invoked_subcommand is not None:
        return

    try:
        require_odoo_project()
    except FileNotFoundError as e:
        ui.exit_with_error(str(e))

    from odoo_rich_cli.menu import interactive_menu

    interactive_menu(config, database)


def _has_flag(argv: Iterable[str], short: str, long: str) -> bool:
    return any(arg in (short, long) or arg.startswith(long + "=") for arg in argv)


def run(config: str | None = None, database: str | None = None) -> None:
    """Launch orc from a project-local cli.py.

        from odoo_rich_cli import run
        if __name__ == "__main__":
            run(config="./config/odoo.conf", database="my_db")

    Defaults are spliced into argv as -c/-d only when not already passed.
    """
    argv = sys.argv[1:]
    inject = []
    if config and not _has_flag(argv, "-c", "--config"):
        inject += ["-c", str(config)]
    if database and not _has_flag(argv, "-d", "--database"):
        inject += ["-d", str(database)]

    sys.argv = [sys.argv[0], *inject, *argv]
    app()
