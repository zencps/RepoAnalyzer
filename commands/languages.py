"""CLI command: language breakdown via GitHub API or local file extensions."""

from pathlib import Path

import typer

from analyzer.files import scan_directory
from analyzer.language import usage_from_extensions
from commands.common import graceful_errors, resolve_analysis
from models.repository import AnalysisReport, LanguageUsage
from utils.formatter import console, humanize_bytes, print_muted, print_warning
from utils.helpers import RepoAnalyzerError, extract_repo_slug
from utils.tables import build_languages_table


def languages(
    source: str = typer.Argument(
        ...,
        help="GitHub URL/slug (owner/name) or path to a local directory.",
    ),
) -> None:
    """Display language percentages with block bars."""
    with graceful_errors():
        usages: list[LanguageUsage] = _collect_language_usage(source)
    if not usages:
        print_warning("No recognized programming-language files found.")
        return
    total_bytes: int = sum(usage.byte_size for usage in usages)
    console.print(build_languages_table(usages))
    print_muted(f"Tracked {humanize_bytes(total_bytes)} across {len(usages)} languages.")


def _collect_language_usage(source: str) -> list[LanguageUsage]:
    candidate: Path = Path(source).expanduser()
    if candidate.is_dir():
        analysis = scan_directory(candidate)
        return usage_from_extensions(analysis.byte_counts)

    if extract_repo_slug(source) is None:
        raise RepoAnalyzerError(
            f"'{source}' is neither an existing directory nor a GitHub repository."
        )
    report: AnalysisReport = resolve_analysis(source)
    return report.languages
