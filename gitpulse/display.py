from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box


_BAR_CHARS = "█▉▊▋▌▍▎▏"
_BAR_WIDTH = 24


def _bar(value: int, max_val: int, width: int = _BAR_WIDTH) -> str:
    if max_val == 0:
        return " " * width
    filled = int(value / max_val * width)
    return "█" * filled + "░" * (width - filled)


class Display:
    def __init__(self, no_color: bool = False) -> None:
        self.console = Console(no_color=no_color, highlight=False)

    # ------------------------------------------------------------------ #
    #  Header / footer                                                     #
    # ------------------------------------------------------------------ #

    def print_header(self, path: str) -> None:
        title = Text()
        title.append("⚡ gitpulse", style="bold white")
        title.append(f"  {path}", style="dim")
        self.console.print()
        self.console.print(Panel(title, border_style="bright_blue", padding=(0, 2)))

    def print_success(self, msg: str) -> None:
        self.console.print(f"\n[bold green]✓[/] {msg}")

    def print_error(self, msg: str) -> None:
        self.console.print(f"\n[bold red]✗ Error:[/] {msg}")

    @contextmanager
    def progress(self, label: str):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as prog:
            prog.add_task(label, total=None)
            yield

    # ------------------------------------------------------------------ #
    #  Summary                                                             #
    # ------------------------------------------------------------------ #

    def print_summary(self, data: dict) -> None:
        self.console.print("\n[bold]📊 Summary[/]", style="bright_blue")

        if data.get("total_commits", 0) == 0:
            self.console.print("  [dim]No commits found.[/]")
            return

        first: datetime = data["first_commit"]
        last: datetime = data["last_commit"]

        cards = [
            _metric("Total commits", str(data["total_commits"])),
            _metric("Contributors", str(data["unique_authors"])),
            _metric("Branches", str(data["branches"])),
            _metric("Active branch", data["active_branch"]),
            _metric("First commit", first.strftime("%Y-%m-%d")),
            _metric("Last commit", last.strftime("%Y-%m-%d")),
            _metric("Repo age", f"{data['age_days']} days"),
        ]
        self.console.print(Columns(cards, equal=False, padding=(0, 2)))

    # ------------------------------------------------------------------ #
    #  Contributors                                                        #
    # ------------------------------------------------------------------ #

    def print_contributors(self, rows: list[dict]) -> None:
        if not rows:
            return

        self.console.print("\n[bold]👥 Top contributors[/]", style="bright_blue")
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold dim")
        table.add_column("#", style="dim", width=3)
        table.add_column("Author", min_width=24)
        table.add_column("Commits", justify="right")
        table.add_column("Additions", justify="right", style="green")
        table.add_column("Deletions", justify="right", style="red")

        max_commits = rows[0]["commits"] if rows else 1
        for i, row in enumerate(rows, 1):
            bar = _bar(row["commits"], max_commits, 14)
            table.add_row(
                str(i),
                row["author"],
                f"[cyan]{row['commits']}[/] [dim]{bar}[/]",
                f"+{row['additions']:,}",
                f"-{row['deletions']:,}",
            )
        self.console.print(table)

    # ------------------------------------------------------------------ #
    #  File churn                                                          #
    # ------------------------------------------------------------------ #

    def print_file_churn(self, rows: list[dict]) -> None:
        if not rows:
            return

        self.console.print("\n[bold]🔥 Most changed files[/]", style="bright_blue")
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold dim")
        table.add_column("#", style="dim", width=3)
        table.add_column("File", min_width=32)
        table.add_column("Lines changed", justify="right")

        max_lines = rows[0]["lines_changed"] if rows else 1
        for i, row in enumerate(rows, 1):
            bar = _bar(row["lines_changed"], max_lines, 16)
            table.add_row(
                str(i),
                row["file"],
                f"[yellow]{row['lines_changed']:,}[/] [dim]{bar}[/]",
            )
        self.console.print(table)

    # ------------------------------------------------------------------ #
    #  Commit activity                                                     #
    # ------------------------------------------------------------------ #

    def print_commit_activity(self, data: dict) -> None:
        self.console.print("\n[bold]📅 Commit activity[/]", style="bright_blue")

        # By weekday
        weekday = data["by_weekday"]
        max_wd = max(weekday.values()) if weekday else 1
        self.console.print("  [dim]By day of week[/]")
        for day, count in weekday.items():
            bar = _bar(count, max_wd, 20)
            self.console.print(f"  [cyan]{day}[/]  [dim]{bar}[/]  [white]{count}[/]")

        # By hour — sparkline style
        self.console.print()
        by_hour = data["by_hour"]
        if by_hour:
            max_h = max(by_hour.values()) if by_hour else 1
            spark = ""
            levels = " ▁▂▃▄▅▆▇█"
            for h in range(24):
                v = by_hour.get(h, 0)
                idx = int(v / max_h * (len(levels) - 1))
                spark += levels[idx]
            self.console.print(f"  [dim]By hour (00–23)[/]  [cyan]{spark}[/]")

        # By month — mini chart
        by_month = data["by_month"]
        if len(by_month) > 1:
            self.console.print()
            self.console.print("  [dim]Monthly activity[/]")
            max_m = max(by_month.values())
            for month, count in list(by_month.items())[-12:]:
                bar = _bar(count, max_m, 20)
                self.console.print(f"  [dim]{month}[/]  [dim]{bar}[/]  [white]{count}[/]")

    # ------------------------------------------------------------------ #
    #  Languages                                                           #
    # ------------------------------------------------------------------ #

    def print_languages(self, rows: list[dict]) -> None:
        if not rows:
            return

        self.console.print("\n[bold]🗂  Language breakdown[/]", style="bright_blue")
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold dim")
        table.add_column("Language", min_width=18)
        table.add_column("Files", justify="right")
        table.add_column("%", justify="right")
        table.add_column("", min_width=24)

        colors = ["cyan", "green", "yellow", "magenta", "blue", "red", "white"]
        max_pct = rows[0]["pct"] if rows else 1
        for i, row in enumerate(rows[:12]):
            color = colors[i % len(colors)]
            bar = _bar(int(row["pct"]), int(max_pct), 20)
            table.add_row(
                f"[{color}]{row['language']}[/]",
                str(row["files"]),
                f"{row['pct']}%",
                f"[dim]{bar}[/]",
            )
        self.console.print(table)
        self.console.print()


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _metric(label: str, value: str) -> Panel:
    content = Text()
    content.append(value + "\n", style="bold white")
    content.append(label, style="dim")
    return Panel(content, border_style="dim", padding=(0, 1), width=20)
