"""Tests for Pydantic domain models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    RepositoryStats,
)


class TestRepositoryStats:
    def test_minimal_local_construction(self) -> None:
        stats = RepositoryStats(full_name="demo (local)", source="local")
        assert stats.source == "local"
        assert stats.stars == 0
        assert stats.total_commits is None

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RepositoryStats(full_name="x", source="svn")

    def test_full_github_construction(self) -> None:
        now = datetime.now(UTC)
        stats = RepositoryStats(
            full_name="octocat/Hello-World",
            source="github",
            url="https://github.com/octocat/Hello-World",
            stars=1_000,
            license={"name": "MIT License", "spdx_id": "MIT"},
            created_at=now,
        )
        assert stats.license is not None
        assert stats.license.spdx_id == "MIT"
        assert stats.created_at == now


class TestCommitInfo:
    def test_requires_sha_and_date(self) -> None:
        with pytest.raises(ValidationError):
            CommitInfo(sha="abc123")

    def test_defaults(self) -> None:
        commit = CommitInfo(
            sha="abc123",
            committed_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        )
        assert commit.author_name == "unknown"
        assert commit.additions is None


class TestContributorInfo:
    def test_commit_count_required(self) -> None:
        with pytest.raises(ValidationError):
            ContributorInfo(name="Ada")

    def test_valid(self) -> None:
        contributor = ContributorInfo(name="Ada", commit_count=42)
        assert contributor.email is None


class TestAnalysisReport:
    def test_collection_defaults(self) -> None:
        report = AnalysisReport(
            repository=RepositoryStats(full_name="r", source="local")
        )
        assert report.commits == []
        assert report.contributors == []
        assert report.languages == []

    def test_holds_nested_models(self) -> None:
        report = AnalysisReport(
            repository=RepositoryStats(full_name="r", source="github"),
            commits=[
                CommitInfo(
                    sha="a" * 40,
                    committed_at=datetime.now(UTC),
                    message="msg",
                )
            ],
        )
        assert len(report.commits) == 1
