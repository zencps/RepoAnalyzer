"""CLI command: export an analysis report as JSON, CSV, Markdown, or HTML."""

from pathlib import Path

import typer

from commands.common import graceful_errors, resolve_analysis
from utils.exporters import export_report
from utils.formatter import humanize_bytes, print_success


def export(
    output: Path = typer.Argument(
        ...,
        help="Destination file; format inferred from .json/.csv/.md/.html.",
    ),
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
        help="Number of contributors to include.",
        min=1,
    ),
    output_format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Override the format instead of inferring it from the extension.",
    ),
) -> None:
    """Write a full analysis report to a file."""
    with graceful_errors():
        report = resolve_analysis(
            source, max_commits=max_commits, contributor_limit=top
        )
        destination: Path = output.expanduser()
        written: Path = export_report(report, destination, fmt=output_format)
    size: int = written.stat().st_size
    print_success(f"Report written to {written} ({humanize_bytes(size)})")
