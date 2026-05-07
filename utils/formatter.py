"""Output formatting utilities: branding, message helpers, and visual charts."""

import sys
from collections.abc import Sequence
from datetime import datetime

from rich.box import DOUBLE
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from utils.theme import REPO_ANALYZER_THEME

APP_VERSION: str = "1.0.0"

SPARK_CHARS: tuple[str, ...] = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")


def _build_console() -> Console:
    """Create the app console, forcing UTF-8 output on Windows so Unicode
    blocks and box-drawing characters survive pipes and redirection."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
    return Console(theme=REPO_ANALYZER_THEME, legacy_windows=False)


console: Console = _build_console()

LOGO_ART: str = r"""
    ____                  ___                __
   / __ \___  ____  ____ /   |  ____  ____ _/ /_  _______  _____
  / /_/ / _ \/ __ \/ __ \ /| | / __ \/ __ `/ / / / /_  / / / / ___/
 / _, _/  __/ /_/ / /_/ / ___ |/ / / / /_/ / / /_/ / /_/ / /
/_/ |_|\___/ .___/\____/_/  |_/_/ /_/\__,_/_/\__, / /___/\___/_/
          /_/                               /____/
""".strip("\n")


def print_logo() -> None:
    """Print the ASCII art banner wrapped in a double-line panel."""
    logo_panel = Panel(
        Text(LOGO_ART, style="primary", justify="center"),
        box=DOUBLE,
        border_style="border",
        title=f"[secondary]v{APP_VERSION}[/]",
        subtitle="[secondary]GitHub & Git Analytics[/]",
    )
    console.print(logo_panel)


def build_language_bar(language: str, percentage: float, width: int = 20) -> Text:
    """Build a block bar like `Python [██████████░░] 73%` as a styled Rich Text."""
    clamped: float = max(0.0, min(percentage, 100.0))
    filled: int = round((clamped / 100) * width)
    empty: int = width - filled

    bar: str = "█" * filled + "░" * empty
    label: str = f"{language:<12}"
    value: str = f"{clamped:>5.1f}%"

    return Text.assemble(
        (label, "primary"),
        ("[", "muted"),
        (bar, "primary"),
        ("]", "muted"),
        (" ", ""),
        (value, "secondary"),
    )


def print_language_bar(language: str, percentage: float, width: int = 20) -> None:
    """Render a single language block bar to the console."""
    console.print(build_language_bar(language, percentage, width))


def generate_sparkline(data: Sequence[int | float]) -> Text:
    """Render a value series as a Unicode block sparkline (e.g. ▂▃▅▇▆▄)."""
    if not data:
        return Text("", style="primary")
    low: int | float = min(data)
    high: int | float = max(data)
    span: int | float = high - low
    chars: list[str] = []
    for value in data:
        if span == 0:
            index: int = len(SPARK_CHARS) // 2
        else:
            index = round((value - low) / span * (len(SPARK_CHARS) - 1))
        chars.append(SPARK_CHARS[index])
    return Text("".join(chars), style="primary")


def humanize_number(value: int | None) -> str:
    """Format integers with thousands separators; em dash when unknown."""
    if value is None:
        return "—"
    return f"{value:,}"


def humanize_bytes(size_bytes: int | None) -> str:
    """Render byte counts as human-readable B/KB/MB/GB/TB strings."""
    if size_bytes is None:
        return "—"
    size: float = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def humanize_size_kb(size_kb: int | None) -> str:
    """Render kilobyte counts (GitHub repo sizes) as readable strings."""
    if size_kb is None:
        return "—"
    return humanize_bytes(size_kb * 1024)


def format_timestamp(value: datetime | None) -> str:
    """Render datetimes as compact YYYY-MM-DD HH:MM strings."""
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


def print_success(message: str) -> None:
    console.print(f"[success]✔[/] [primary]{message}[/]")


def print_warning(message: str) -> None:
    console.print(f"[warning]⚠ {message}[/]")


def print_error(message: str) -> None:
    console.print(f"[error]✘ {message}[/]")


def print_muted(message: str) -> None:
    console.print(f"[muted]{message}[/]")
