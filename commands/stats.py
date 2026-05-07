"""CLI command: analyze repository stats from GitHub or a local Git path."""

import typer

from commands.common import graceful_errors, resolve_analysis
from models.repository import AnalysisReport
from utils.tables import render_report


def stats(
    source: str = typer.Argument(
        ...,
        help="GitHub URL/slug (owner/name) or path to a local Git repository.",
    ),
    max_commits: int | None = typer.Option(
        None,
        "--max-commits",
        help="Cap the number of commits fetched (GitHub API).",
        min=1,
    ),
    top: int = typer.Option(
        10,
        "--top",
        help="Show only the top N contributors.",
        min=1,
    ),
) -> None:
    """Display stars, forks, issues, license, dates, commits, and contributors."""
    with graceful_errors():
        report: AnalysisReport = resolve_analysis(
            source, max_commits=max_commits, contributor_limit=top
        )
    render_report(report)
