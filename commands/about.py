"""CLI command: environment and configuration summary."""

import platform

import typer

from analyzer.github import GitHubAnalyzer
from commands.common import graceful_errors
from utils.config import get_settings
from utils.formatter import APP_VERSION, console, print_muted
from utils.helpers import mask_secret
from utils.tables import build_about_table


def about(
    check_api: bool = typer.Option(
        False,
        "--check-api",
        help="Ping the GitHub API and show the remaining rate limit.",
    ),
) -> None:
    """Show version, platform, token status, and configured paths."""
    settings = get_settings()
    with graceful_errors():
        table = build_about_table(
            version=f"v{APP_VERSION}",
            python_version=platform.python_version(),
            operating_system=f"{platform.system()} {platform.release()}",
            token_display=mask_secret(settings.github_token),
            token_source=settings.token_source,
            clone_dir=str(settings.clone_base_dir),
        )
        console.print(table)

        if not check_api:
            return

        analyzer = GitHubAnalyzer(token=settings.github_token)
        try:
            remaining: int = analyzer.check_connection()
        except Exception as exc:
            print_muted(f"API check failed: {exc}")
            return
        print_muted(f"GitHub API reachable — {remaining} requests remaining.")
