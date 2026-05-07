"""Local Git analyzer: repository opening, cloning, and history extraction."""

import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from git import Actor, Commit, Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.remote import RemoteProgress
from rich.progress import BarColumn, Progress, TaskID, TaskProgressColumn, TextColumn

from analyzer.contributors import rank_contributors
from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    RepositoryStats,
)
from utils.helpers import RepoAnalyzerError, extract_repo_slug

logger: logging.Logger = logging.getLogger(__name__)


class InvalidRepositoryError(RepoAnalyzerError):
    """Raised when a path is not a usable Git working copy."""


def suggest_clone_dir(url: str, base_dir: Path) -> Path:
    """Derive `<base>/<repo-name>` from a Git remote URL."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    name: str = parsed.path.rstrip("/").rpartition("/")[2].removesuffix(".git")
    return base_dir / (name or "repository")


def clone_repository(url: str, destination: Path) -> Path:
    """Clone `url` into `destination` with an animated Rich progress bar."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task_id: TaskID = progress.add_task("[primary]Cloning…", total=None)
        bridge: _CloneProgressBridge = _CloneProgressBridge(progress, task_id)
        try:
            Repo.clone_from(url, str(destination), progress=bridge)
        except GitCommandError as exc:
            detail: str = (exc.stderr or str(exc)).strip().splitlines()[-1]
            raise InvalidRepositoryError(f"Clone failed for '{url}': {detail}") from exc
    return destination


class _CloneProgressBridge(RemoteProgress):
    """Bridges GitPython clone progress into a Rich Progress task."""

    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        super().__init__()
        self._progress: Progress = progress
        self._task_id: TaskID = task_id

    def __call__(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str = "",
    ) -> None:
        self.update(op_code, cur_count, max_count, message)

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str = "",
    ) -> None:
        stage: str = self._stage_label(op_code)
        total: int | None = _as_int(max_count)
        done: int | None = _as_int(cur_count)
        if total is not None and total > 0 and done is not None:
            self._progress.update(
                self._task_id,
                description=f"[primary]{stage}",
                total=total,
                completed=done,
            )
        elif stage:
            self._progress.update(self._task_id, description=f"[primary]{stage}")

    @staticmethod
    def _stage_label(op_code: int) -> str:
        if op_code & RemoteProgress.RECEIVING:
            return "Receiving objects"
        if op_code & RemoteProgress.WRITING:
            return "Writing objects"
        if op_code & RemoteProgress.RESOLVING:
            return "Resolving deltas"
        if op_code & RemoteProgress.COMPRESSING:
            return "Compressing objects"
        if op_code & RemoteProgress.COUNTING:
            return "Counting objects"
        return ""


def _as_int(value: int | float | str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def open_repository(path: Path) -> Repo:
    """Open and validate a local Git working copy."""
    resolved: Path = path.expanduser().resolve()
    if not resolved.exists():
        raise InvalidRepositoryError(f"Path does not exist: {resolved}")
    try:
        return Repo(resolved)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise InvalidRepositoryError(f"Not a Git repository: {resolved}") from exc


def collect_stats(repo: Repo, local_path: Path) -> RepositoryStats:
    """Build repository-level stats from a local working copy."""
    origin_url: str | None = _origin_url(repo)
    slug: str | None = extract_repo_slug(origin_url) if origin_url else None

    branch: str = "HEAD"
    try:
        if not repo.head.is_detached:
            branch = repo.active_branch.name
    except TypeError:
        logger.debug("Detached or unborn HEAD in %s", local_path)

    total_commits: int | None = None
    pushed_at: datetime | None = None
    try:
        total_commits = int(repo.git.rev_list("--count", "HEAD"))
        pushed_at = repo.head.commit.committed_datetime
    except (GitCommandError, ValueError) as exc:
        logger.warning("Repository at %s has no commits yet (%s)", local_path, exc)

    return RepositoryStats(
        full_name=slug or f"{local_path.name} (local)",
        source="local",
        url=origin_url or "",
        default_branch=branch,
        total_commits=total_commits,
        pushed_at=pushed_at,
        local_path=local_path,
    )


def iter_commits(
    repo: Repo,
    max_commits: int | None = None,
    *,
    include_diff_stats: bool = False,
) -> list[CommitInfo]:
    """Return normalized commit info, newest first."""
    results: list[CommitInfo] = []
    stream: Iterator[Commit] = iter(())
    try:
        stream = iter(repo.iter_commits("HEAD"))
    except GitCommandError as exc:
        logger.warning("No commit history available: %s", exc)
        return results
    for index, raw in enumerate(stream):
        if max_commits is not None and index >= max_commits:
            break
        author: Actor = raw.author
        info = CommitInfo(
            sha=str(raw.hexsha),
            committed_at=raw.committed_datetime,
            message=str(raw.message or ""),
            author_name=getattr(author, "name", None) or "unknown",
            author_email=getattr(author, "email", None),
        )
        if include_diff_stats:
            _attach_diff_stats(raw, info)
        results.append(info)
    return results


def _attach_diff_stats(raw: Commit, info: CommitInfo) -> None:
    try:
        totals = raw.stats.total
        info.additions = int(totals["insertions"])
        info.deletions = int(totals["deletions"])
        info.files_changed = int(totals["files"])
    except Exception as exc:
        logger.debug("No diff stats for %s (%s)", info.sha[:8], exc)


def collect_contributors(repo: Repo, top: int | None = None) -> list[ContributorInfo]:
    """Aggregate commit counts per author across HEAD history."""
    return rank_contributors(iter_commits(repo), top)


def build_report(
    local_path: Path,
    *,
    max_commits: int | None = None,
) -> AnalysisReport:
    """Convenience entry point mirroring GitHubAnalyzer.build_report."""
    repo: Repo = open_repository(local_path)
    stats: RepositoryStats = collect_stats(repo, local_path)
    commits: list[CommitInfo] = iter_commits(
        repo, max_commits, include_diff_stats=True
    )
    contributors: list[ContributorInfo] = rank_contributors(commits)
    return AnalysisReport(
        repository=stats,
        commits=commits,
        contributors=contributors,
    )


def _origin_url(repo: Repo) -> str | None:
    try:
        urls: list[str] = list(repo.remotes.origin.urls)
    except AttributeError:
        return None
    return urls[0] if urls else None
