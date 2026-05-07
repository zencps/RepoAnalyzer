"""RepoAnalyzer CLI — GitHub & Git repository analytics from your terminal."""

import logging
import os

import typer
from rich.logging import RichHandler

from commands import about as about_command
from commands import clone as clone_command
from commands import commits as commits_command
from commands import contributors as contributors_command
from commands import export as export_command
from commands import languages as languages_command
from commands import stats as stats_command
from utils.formatter import APP_VERSION, console, print_logo

app: typer.Typer = typer.Typer(
    name="repo-analyzer",
    help="Analyze GitHub repositories and local Git workspaces.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _configure_logging() -> None:
    level: int = (
        logging.DEBUG if os.environ.get("REPO_ANALYZER_DEBUG") else logging.INFO
    )
    handler: RichHandler = RichHandler(
        console=console,
        show_path=False,
        show_time=False,
        rich_tracebacks=False,
    )
    logging.basicConfig(level=level, format="%(message)s", handlers=[handler])


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the application version and exit.",
    ),
) -> None:
    """Print branding before every command and handle global options."""
    print_logo()
    if version:
        console.print(f"[primary]RepoAnalyzer[/] [secondary]v{APP_VERSION}[/]")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print("[secondary]Run [primary]--help[/] to see available commands.[/]")


app.command(name="clone", help="Clone a Git repository locally.")(clone_command.clone)
app.command(name="stats", help="Show repository statistics.")(stats_command.stats)
app.command(name="commits", help="Commit analytics with activity sparklines.")(
    commits_command.commits
)
app.command(name="contributors", help="Rank contributors by commit count.")(
    contributors_command.contributors
)
app.command(name="languages", help="Language breakdown with block bars.")(
    languages_command.languages
)
app.command(name="export", help="Export a report (json/csv/md/html).")(
    export_command.export
)
app.command(name="about", help="Show environment and configuration summary.")(
    about_command.about
)

_configure_logging()

if __name__ == "__main__":
    app()
