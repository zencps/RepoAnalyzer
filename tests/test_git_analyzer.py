"""Tests for the local Git analyzer (offline, fixture-based)."""

from pathlib import Path

import pytest
from git import Repo

from analyzer.git import (
    build_report,
    collect_contributors,
    collect_stats,
    iter_commits,
    open_repository,
    suggest_clone_dir,
)
from utils.helpers import RepoAnalyzerError, extract_repo_slug


class TestOpenRepository:
    def test_opens_valid_repo(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        repo = open_repository(path)
        assert str(repo.working_dir) == str(path)

    def test_rejects_plain_directory(self, tmp_path: Path) -> None:
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        with pytest.raises(RepoAnalyzerError, match="Not a Git repository"):
            open_repository(plain)

    def test_rejects_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(RepoAnalyzerError, match="does not exist"):
            open_repository(tmp_path / "missing")


class TestCollectStats:
    def test_basic_fields(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        stats = collect_stats(local_repo, path)
        assert stats.source == "local"
        assert stats.full_name == "sample (local)"
        assert stats.default_branch in {"master", "main"}
        assert stats.total_commits == 3
        assert stats.pushed_at is not None
        assert stats.local_path == path


class TestIterCommits:
    def test_returns_newest_first(self, local_repo: Repo) -> None:
        commits = iter_commits(local_repo)
        messages = [c.message for c in commits]
        assert messages == ["tweak app", "add app", "initial commit"]
        assert all(len(c.sha) == 40 for c in commits)

    def test_max_commits_limit(self, local_repo: Repo) -> None:
        assert len(iter_commits(local_repo, max_commits=2)) == 2


class TestCollectContributors:
    def test_ranked_by_count(self, local_repo: Repo) -> None:
        contributors = collect_contributors(local_repo)
        assert [c.name for c in contributors] == ["Ada Lovelace", "Grace Hopper"]
        assert contributors[0].commit_count == 2
        assert contributors[0].email == "ada@example.com"

    def test_top_n(self, local_repo: Repo) -> None:
        top = collect_contributors(local_repo, top=1)
        assert len(top) == 1
        assert top[0].name == "Ada Lovelace"


class TestBuildReport:
    def test_aggregates_everything(self, local_repo: Repo) -> None:
        report = build_report(Path(local_repo.working_dir), max_commits=10)
        assert report.repository.total_commits == 3
        assert len(report.commits) == 3
        assert len(report.contributors) == 2


class TestSlugHelpers:
    def test_suggest_clone_dir(self) -> None:
        target = suggest_clone_dir(
            "https://github.com/octocat/Hello-World.git",
            base_dir=Path("/tmp/x"),
        )
        assert target == Path("/tmp/x/Hello-World")

    def test_extract_slug_variants(self) -> None:
        assert extract_repo_slug("https://github.com/a/b") == "a/b"
        assert extract_repo_slug("git@github.com:a/b.git") == "a/b"
        assert extract_repo_slug("a/b") == "a/b"
        assert extract_repo_slug("https://gitlab.com/a/b") is None
