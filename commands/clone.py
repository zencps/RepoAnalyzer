"""CLI command: clone a remote Git repository locally."""

from pathlib import Path

import typer

from analyzer.git import clone_repository, suggest_clone_dir
from commands.common import graceful_errors
from utils.config import get_settings
from utils.formatter import print_error, print_success


def clone(
    url: str = typer.Argument(..., help="Git remote URL to clone."),
    dest: Path | None = typer.Option(
        None,
        "--dest",
        "-d",
        help="Target directory (default: ./repos/<repo-name>).",
    ),
) -> None:
    """Clone a Git repository with a live progress bar."""
    with graceful_errors():
        target: Path = (
            dest.expanduser()
            if dest is not None
            else suggest_clone_dir(url, get_settings().clone_base_dir)
        )
        if target.exists() and any(target.iterdir()):
            print_error(f"Destination already exists and is not empty: {target}")
            raise typer.Exit(code=1)
        path: Path = clone_repository(url, target)
    print_success(f"Cloned into {path}")
