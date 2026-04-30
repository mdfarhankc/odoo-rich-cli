from typing import Any, NoReturn

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

console = Console()

STATE_COLORS = {
    "installed": "green",
    "uninstalled": "dim",
    "to upgrade": "yellow",
    "to install": "cyan",
    "to remove": "red",
}


def _panel(message: str, title: str, color: str) -> None:
    console.print(
        Panel(f"[{color}]{message}[/]", title=f"[bold {color}]{title}[/]", border_style=color)
    )


def show_success(message: str, title: str = "Success") -> None:
    _panel(message, title, "green")


def show_failure(message: str, title: str = "Failed") -> None:
    _panel(message, title, "red")


def show_warning(message: str, title: str = "Result") -> None:
    _panel(message, title, "yellow")


def exit_with_error(message: str) -> NoReturn:
    show_failure(message, title="Error")
    raise typer.Exit(1)


def show_result(result: Any) -> None:
    if result.success:
        show_success(result.message)
    else:
        show_failure(result.message)


def render_module_info(data: dict[str, Any] | None) -> None:
    if not data:
        return

    state = data.get("state", "")
    color = STATE_COLORS.get(state, "white")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold", width=16)
    table.add_column()

    table.add_row("Name", data.get("name", ""))
    table.add_row("Technical Name", data.get("technical_name", ""))
    table.add_row("State", f"[{color}]{state}[/]")
    table.add_row("Version", data.get("version", ""))
    table.add_row("Author", data.get("author", ""))
    table.add_row("Summary", data.get("summary", ""))

    deps = data.get("dependencies", [])
    table.add_row("Dependencies", ", ".join(deps) if deps else "[dim]none[/]")

    rev_deps = data.get("reverse_dependencies", [])
    table.add_row("Dependents", ", ".join(rev_deps) if rev_deps else "[dim]none[/]")

    console.print(
        Panel(table, title="[bold]Module Info[/]", border_style="bright_blue", padding=(1, 2))
    )


def render_module_list(data: list[dict[str, Any]] | None, message: str) -> None:
    if not data:
        show_warning(message)
        return

    table = Table(title=message, border_style="bright_blue", header_style="bold")
    table.add_column("#", style="dim", width=5, justify="right")
    table.add_column("Technical Name", style="bold")
    table.add_column("Name")
    table.add_column("State")
    table.add_column("Version", style="dim")

    for i, m in enumerate(data, 1):
        state = m.get("state", "")
        color = STATE_COLORS.get(state, "white")
        table.add_row(
            str(i),
            m.get("technical_name", ""),
            m.get("name", ""),
            f"[{color}]{state}[/]",
            m.get("version", ""),
        )

    console.print(table)


def render_cron_list(data: list[dict[str, Any]] | None, message: str) -> None:
    if not data:
        show_warning(message)
        return

    table = Table(title=message, border_style="bright_blue", header_style="bold")
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Name", style="bold")
    table.add_column("Active")
    table.add_column("Interval", style="dim")
    table.add_column("Model", style="dim")

    for c in data:
        active_str = "[green]ON[/]" if c.get("active") else "[red]OFF[/]"
        interval = f"{c.get('interval_number', '')} {c.get('interval_type', '')}"
        table.add_row(
            str(c.get("id", "")),
            c.get("name", ""),
            active_str,
            interval,
            c.get("model", ""),
        )

    console.print(table)
    console.print()
    console.print("[dim]  Use [bold]orc cron-toggle -i <ID>[/] to toggle a specific cron.[/]")


def render_db_list(data: list[str] | None, message: str) -> None:
    if not data:
        show_warning(message)
        return

    table = Table(title=message, border_style="bright_blue", header_style="bold")
    table.add_column("#", style="dim", width=5, justify="right")
    table.add_column("Database", style="bold")

    for i, name in enumerate(data, 1):
        table.add_row(str(i), name)

    console.print(table)


def status(label: str, db_name: str, target: str = "") -> Status:
    db = db_name or "(auto)"
    if target:
        text = f"  [bold cyan]{label}[/] [yellow]{target}[/] on [bold]{db}[/]..."
    else:
        text = f"  [bold cyan]{label}[/] on [bold]{db}[/]..."
    return console.status(text, spinner="dots")
