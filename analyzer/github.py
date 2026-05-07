"""GitHub analyzer: a read-only facade over the GitHub REST API via PyGithub."""

import logging
from typing import Any

from github import (
    Auth,
    BadCredentialsException,
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.Repository import Repository

from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    LanguageUsage,
    LicenseInfo,
    RepositoryStats,
)
from utils.helpers import RepoAnalyzerError, extract_repo_slug

logger: logging.Logger = logging.getLogger(__name__)

EMPTY_REPO_STATUSES: frozenset[int] = frozenset({204, 409})
LOW_RATE_LIMIT_THRESHOLD: int = 10


class GitHubAuthError(RepoAnalyzerError):
    """Raised when the configured token is rejected."""


class GitHubRateLimitError(RepoAnalyzerError):
    """Raised when the API rate limit is exhausted."""


class RepositoryNotFoundError(RepoAnalyzerError):
    """Raised when a repository cannot be resolved."""


def _translate_github_error(exc: GithubException, context: str) -> RepoAnalyzerError:
    if isinstance(exc, RateLimitExceededException):
        return GitHubRateLimitError(
            "GitHub rate limit exceeded. Set GITHUB_TOKEN in .env or config.toml."
        )
    if isinstance(exc, BadCredentialsException):
        return GitHubAuthError("GitHub rejected the configured token.")
    if isinstance(exc, UnknownObjectException):
        return RepositoryNotFoundError(f"Repository not found: {context}")
    message: Any = getattr(exc, "data", exc)
    if isinstance(message, dict):
        message = message.get("message", "")
    return RepoAnalyzerError(f"GitHub API error ({exc.status}) for {context}: {message}")


class GitHubAnalyzer:
    """Fetches repository statistics, languages, commits, and contributors."""

    def __init__(self, token: str | None = None) -> None:
        self.token: str | None = token
        self._client: Github = Github(auth=Auth.Token(token)) if token else Github()

    @property
    def rate_limit_remaining(self) -> int | None:
        try:
            remaining: int = self._client.rate_limiting[0]
        except GithubException:
            return None
        return remaining

    def check_connection(self) -> int:
        """Ping the API and return remaining core requests; logs when low."""
        remaining: int
        limit: int
        remaining, limit = self._client.rate_limiting
        if remaining <= LOW_RATE_LIMIT_THRESHOLD:
            logger.warning("Low GitHub rate limit: %s/%s requests left.", remaining, limit)
        return remaining

    def get_repository(self, source: str) -> Repository:
        """Resolve a URL or `owner/name` slug to a PyGithub Repository object."""
        slug: str | None = extract_repo_slug(source)
        if slug is None:
            raise RepositoryNotFoundError(f"Unrecognized GitHub source: '{source}'")
        try:
            return self._client.get_repo(slug)
        except GithubException as exc:
            raise _translate_github_error(exc, slug) from exc

    def build_stats(self, repo: Repository) -> RepositoryStats:
        license_info: LicenseInfo | None = None
        raw_license = repo.license
        if raw_license is not None:
            license_info = LicenseInfo(
                name=getattr(raw_license, "name", None) or "Unknown",
                spdx_id=getattr(raw_license, "spdx_id", None),
            )
        watchers: int = (
            repo.subscribers_count
            if repo.subscribers_count is not None
            else repo.watchers_count
        )
        return RepositoryStats(
            full_name=repo.full_name,
            source="github",
            url=repo.html_url,
            description=repo.description,
            default_branch=repo.default_branch or "HEAD",
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            open_issues=repo.open_issues_count,
            watchers=watchers,
            size_kb=repo.size,
            total_commits=self._safe_total_commits(repo),
            total_contributors=self._safe_total_contributors(repo),
            license=license_info,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            pushed_at=repo.pushed_at,
        )

    def fetch_languages(self, repo: Repository) -> list[LanguageUsage]:
        try:
            raw: dict[str, Any] = dict(repo.get_languages())
        except GithubException as exc:
            if exc.status in EMPTY_REPO_STATUSES:
                return []
            raise _translate_github_error(exc, repo.full_name) from exc
        return [
            LanguageUsage(name=name, byte_size=int(size))
            for name, size in raw.items()
            if isinstance(size, int) and not isinstance(size, bool)
        ]

    def fetch_commits(
        self,
        repo: Repository,
        max_commits: int | None = None,
    ) -> list[CommitInfo]:
        results: list[CommitInfo] = []
        try:
            iterator = iter(repo.get_commits())
            while max_commits is None or len(results) < max_commits:
                raw = next(iterator, None)
                if raw is None:
                    break
                git_commit = raw.commit
                author = git_commit.author
                committer = git_commit.committer
                results.append(
                    CommitInfo(
                        sha=raw.sha,
                        committed_at=committer.date
                        if committer is not None
                        else author.date,
                        message=git_commit.message or "",
                        author_name=(author.name if author else None) or "unknown",
                        author_email=author.email if author else None,
                    )
                )
        except GithubException as exc:
            if exc.status in EMPTY_REPO_STATUSES:
                return results
            raise _translate_github_error(exc, repo.full_name) from exc
        return results

    def fetch_contributors(
        self,
        repo: Repository,
        limit: int | None = None,
    ) -> list[ContributorInfo]:
        results: list[ContributorInfo] = []
        try:
            iterator = iter(repo.get_contributors())
            while limit is None or len(results) < limit:
                entry = next(iterator, None)
                if entry is None:
                    break
                name: str = entry.name or entry.login or "anonymous"
                results.append(
                    ContributorInfo(
                        name=name,
                        commit_count=int(entry.contributions or 0),
                        email=entry.email,
                        profile_url=entry.html_url,
                    )
                )
        except GithubException as exc:
            if exc.status in EMPTY_REPO_STATUSES:
                return results
            raise _translate_github_error(exc, repo.full_name) from exc
        return results

    def build_report(
        self,
        source: str,
        *,
        max_commits: int | None = None,
        contributor_limit: int | None = None,
    ) -> AnalysisReport:
        """One-call analysis used by CLI commands."""
        repo: Repository = self.get_repository(source)
        stats: RepositoryStats = self.build_stats(repo)
        logger.debug("Fetched stats for %s", stats.full_name)
        return AnalysisReport(
            repository=stats,
            languages=self.fetch_languages(repo),
            commits=self.fetch_commits(repo, max_commits),
            contributors=self.fetch_contributors(repo, contributor_limit),
        )

    def _safe_total_commits(self, repo: Repository) -> int | None:
        try:
            count: int = repo.get_commits().totalCount
        except GithubException:
            return None
        return count

    def _safe_total_contributors(self, repo: Repository) -> int | None:
        try:
            count: int = repo.get_contributors().totalCount
        except GithubException:
            return None
        return count
