"""Shared utilities: error hierarchy, secret masking, repository slug parsing."""

import re


class RepoAnalyzerError(RuntimeError):
    """Base class for every RepoAnalyzer failure."""


_GITHUB_URL_RE: re.Pattern[str] = re.compile(
    r"github\.com[/:](?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
)
_BARE_SLUG_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def extract_repo_slug(source: str) -> str | None:
    """Return `owner/name` from a GitHub URL or bare slug, else None."""
    text: str = source.strip()
    match: re.Match[str] | None = _GITHUB_URL_RE.search(text)
    if match:
        name: str = match.group("repo").removesuffix(".git")
        return f"{match.group('owner')}/{name}"
    if _BARE_SLUG_RE.match(text):
        return text.removesuffix(".git")
    return None


def mask_secret(secret: str | None) -> str:
    """Mask a token for safe display in logs and UI."""
    if not secret:
        return "<not set>"
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"
