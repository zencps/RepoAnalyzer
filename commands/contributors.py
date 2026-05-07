"""CLI command: ranked contributor listing."""

import typer

from commands.common import graceful_errors, resolve_analysis
from models.repository import AnalysisReport
from utils.formatter import console, print_muted
from utils.tables import build_contributors_table


def contributors(
    source: str = typer.Argument(
        ...,
        help="GitHub URL/slug (owner/name) or path to a local Git repository.",
    ),
    top: int = typer.Option(
        10,
        "--top",
        help="Show only the top N contributors.",
        min=1,
    ),
) -> None:
    """List the most active contributors by commit count."""
    with graceful_errors():
        report: AnalysisReport = resolve_analysis(source, contributor_limit=top)
        ranked = report.contributors[:top]
    print_muted(f"{report.repository.full_name} — showing {len(ranked)}")
    console.print(build_contributors_table(ranked))
