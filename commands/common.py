"""Shared helpers for CLI command modules."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import typer

from analyzer.git import InvalidRepositoryError
from analyzer.git import build_report as build_local_report
from analyzer.github import GitHubAnalyzer
from analyzer.statistics import enrich_report
from models.repository import AnalysisReport
from utils.config import get_settings
from utils.formatter import print_error, print_muted, print_warning
from utils.helpers import RepoAnalyzerError, extract_repo_slug, mask_secret

LOW_LIMIT_NOTICE: int = 10


@contextmanager
def graceful_errors() -> Iterator[None]:
    """Translate domain errors into friendly messages and exit code 1."""
    try:
        yield
    except RepoAnalyzerError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc


def resolve_analysis(
    source: str,
    *,
    max_commits: int | None = None,
    contributor_limit: int | None = None,
) -> AnalysisReport:
    """Resolve a path or GitHub source into a fully populated, enriched report."""
    candidate: Path = Path(source).expanduser()
    if candidate.exists():
        return enrich_report(build_local_report(candidate, max_commits=max_commits))

    if extract_repo_slug(source) is None:
        raise InvalidRepositoryError(
            f"'{source}' is neither an existing directory nor a GitHub repository."
        )

    token: str | None = get_settings().github_token
    if token:
        print_muted(f"Authenticating with GitHub token {mask_secret(token)}")
    else:
        print_warning("No GitHub token configured — unauthenticated limits apply.")

    analyzer: GitHubAnalyzer = GitHubAnalyzer(token=token)
    remaining: int = analyzer.check_connection()
    report: AnalysisReport = analyzer.build_report(
        source,
        max_commits=max_commits,
        contributor_limit=contributor_limit,
    )
    if remaining <= LOW_LIMIT_NOTICE:
        print_warning(f"Low API rate limit: {remaining} requests remaining.")
    return enrich_report(report)


def show_hint(message: str) -> None:
    print_muted(f"{message}")
