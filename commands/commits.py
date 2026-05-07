"""CLI command: commit-history analytics with activity sparklines."""

import typer

from analyzer.commits import monthly_activity
from commands.common import graceful_errors, resolve_analysis
from models.repository import AnalysisReport, CommitStatistics
from utils.formatter import console
from utils.tables import build_commit_analytics_panel


def commits(
    source: str = typer.Argument(
        ...,
        help="GitHub URL/slug (owner/name) or path to a local Git repository.",
    ),
    months: int = typer.Option(
        12,
        "--months",
        help="Trailing month window for the activity sparkline.",
        min=1,
        max=48,
    ),
    max_commits: int | None = typer.Option(
        None,
        "--max-commits",
        help="Cap the number of commits fetched (GitHub API).",
        min=1,
    ),
) -> None:
    """Show totals, averages, peak months, and an activity sparkline."""
    with graceful_errors():
        report: AnalysisReport = resolve_analysis(source, max_commits=max_commits)
        stats_model: CommitStatistics = (
            report.commit_statistics
            if report.commit_statistics is not None
            else CommitStatistics()
        )
        series: list[int] = monthly_activity(report.commits, months)
    console.print(
        build_commit_analytics_panel(stats_model, series, subtitle=report.repository.full_name)
    )
