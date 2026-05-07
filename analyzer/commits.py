"""Commit-history analytics over normalized CommitInfo records."""

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

from models.repository import CommitInfo, CommitStatistics


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _month_key(value: datetime) -> str:
    utc: datetime = _as_utc(value)
    return f"{utc.year:04d}-{utc.month:02d}"


def compute_commit_statistics(commits: Sequence[CommitInfo]) -> CommitStatistics:
    """Derive totals, averages, extremes, and peak month from a history."""
    if not commits:
        return CommitStatistics()

    ordered: list[CommitInfo] = sorted(commits, key=lambda c: _as_utc(c.committed_at))
    total: int = len(ordered)
    oldest: CommitInfo = ordered[0]
    latest: CommitInfo = ordered[-1]

    span_seconds: float = (
        _as_utc(latest.committed_at) - _as_utc(oldest.committed_at)
    ).total_seconds()
    span_days: float = span_seconds / 86_400
    inclusive_days: int = int(span_days) + 1
    active_days: int = len({_as_utc(c.committed_at).date() for c in ordered})
    avg_per_day: float = round(total / inclusive_days, 2)

    month_counts: Counter[str] = Counter(_month_key(c.committed_at) for c in ordered)
    peak_month: str
    peak_count: int
    peak_month, peak_count = month_counts.most_common(1)[0]

    sizes: list[int] = [
        commit.additions + commit.deletions
        for commit in ordered
        if commit.additions is not None and commit.deletions is not None
    ]
    avg_size: float | None = (
        round(sum(sizes) / len(sizes), 1) if sizes else None
    )

    return CommitStatistics(
        total_commits=total,
        avg_per_day=avg_per_day,
        active_days=active_days,
        span_days=round(span_days, 2),
        oldest_at=oldest.committed_at,
        latest_at=latest.committed_at,
        oldest_sha=oldest.sha,
        latest_sha=latest.sha,
        most_active_month=peak_month,
        most_active_month_count=peak_count,
        avg_commit_size=avg_size,
    )


def monthly_activity(
    commits: Sequence[CommitInfo],
    months: int = 12,
) -> list[int]:
    """Per-month commit counts for the trailing window ending at the newest commit.

    Months with zero activity are included so sparklines show true valleys.
    """
    window: int = max(months, 1)
    if not commits:
        return [0] * window

    buckets: Counter[str] = Counter(_month_key(c.committed_at) for c in commits)
    latest: datetime = max(_as_utc(c.committed_at) for c in commits)

    year: int = latest.year
    month: int = latest.month
    series: list[int] = []
    for _ in range(window):
        series.append(buckets.get(f"{year:04d}-{month:02d}", 0))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    series.reverse()
    return series
