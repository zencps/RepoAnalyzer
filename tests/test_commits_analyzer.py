"""Tests for commit-history analytics."""

from datetime import UTC, datetime
from itertools import count

from analyzer.commits import compute_commit_statistics, monthly_activity
from models.repository import CommitInfo

_sha_counter = count()


def make_commit(
    year: int,
    month: int,
    day: int,
    *,
    additions: int | None = None,
    deletions: int | None = None,
    author: str = "Ada",
) -> CommitInfo:
    return CommitInfo(
        sha=f"{next(_sha_counter):040x}",
        committed_at=datetime(year, month, day, 12, 0, tzinfo=UTC),
        message="m",
        author_name=author,
        additions=additions,
        deletions=deletions,
    )


class TestComputeCommitStatistics:
    def test_empty_history(self) -> None:
        stats = compute_commit_statistics([])
        assert stats.total_commits == 0
        assert stats.most_active_month is None
        assert stats.avg_commit_size is None

    def test_totals_and_extremes(self) -> None:
        commits = [
            make_commit(2026, 8, 10),
            make_commit(2026, 1, 5),
            make_commit(2026, 3, 1),
        ]
        stats = compute_commit_statistics(commits)
        assert stats.total_commits == 3
        assert stats.oldest_at == datetime(2026, 1, 5, 12, tzinfo=UTC)
        assert stats.latest_at == datetime(2026, 8, 10, 12, tzinfo=UTC)
        assert stats.oldest_sha == commits[1].sha
        assert stats.latest_sha == commits[0].sha

    def test_most_active_month(self) -> None:
        commits = [
            make_commit(2026, 5, 1),
            make_commit(2026, 5, 2),
            make_commit(2026, 5, 3),
            make_commit(2026, 6, 1),
        ]
        stats = compute_commit_statistics(commits)
        assert stats.most_active_month == "2026-05"
        assert stats.most_active_month_count == 3

    def test_avg_per_day_inclusive_span(self) -> None:
        commits = [make_commit(2026, 1, 1), make_commit(2026, 1, 4)]
        stats = compute_commit_statistics(commits)
        assert stats.span_days == 3.0
        assert stats.avg_per_day == round(2 / 4, 2)
        assert stats.active_days == 2

    def test_avg_commit_size_ignores_unknowns(self) -> None:
        commits = [
            make_commit(2026, 1, 1, additions=10, deletions=2),
            make_commit(2026, 1, 2, additions=None, deletions=None),
            make_commit(2026, 1, 3, additions=6, deletions=2),
        ]
        stats = compute_commit_statistics(commits)
        assert stats.avg_commit_size == (12 + 8) / 2


class TestMonthlyActivity:
    def test_empty_history_returns_zero_window(self) -> None:
        assert monthly_activity([], months=6) == [0] * 6

    def test_window_pads_missing_months_with_zeros(self) -> None:
        commits = [
            make_commit(2026, 7, 15),
            make_commit(2026, 7, 20),
            make_commit(2026, 5, 3),
        ]
        series = monthly_activity(commits, months=4)
        assert series == [0, 1, 0, 2]

    def test_series_ends_at_latest_commit_month(self) -> None:
        commits = [make_commit(2025, 12, 31)]
        series = monthly_activity(commits, months=3)
        assert series == [0, 0, 1]
