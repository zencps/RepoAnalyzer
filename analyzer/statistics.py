"""Cross-cutting enrichment of AnalysisReport instances."""

from datetime import UTC, datetime

from analyzer.commits import compute_commit_statistics, monthly_activity
from analyzer.language import compute_shares
from models.repository import (
    AnalysisReport,
    HealthBreakdown,
    HealthScore,
)

_RECENCY_TIERS: tuple[tuple[int, int], ...] = (
    (7, 30),
    (30, 26),
    (90, 20),
    (180, 14),
    (365, 8),
)
_ACTIVITY_TIERS: tuple[tuple[int, int], ...] = ((30, 25), (7, 18), (2, 10), (1, 6))
_COMMUNITY_TIERS: tuple[tuple[int, int], ...] = ((10, 20), (5, 16), (2, 10), (1, 5))
_STARS_TIERS: tuple[tuple[int, int], ...] = ((1000, 10), (100, 8), (10, 5), (1, 2))
_LOCAL_COMMIT_TIERS: tuple[tuple[int, int], ...] = ((500, 10), (100, 8), (20, 5))


def _tier_points(value: int, tiers: tuple[tuple[int, int], ...]) -> int:
    for threshold, points in tiers:
        if value >= threshold:
            return points
    return 0


def _recency_days(
    report: AnalysisReport,
    now: datetime,
) -> int | None:
    repo = report.repository
    reference = repo.pushed_at or (
        report.commit_statistics.latest_at if report.commit_statistics else None
    )
    if reference is None:
        return None
    delta = now - reference
    return max(delta.days, 0)


def _engagement_points(report: AnalysisReport) -> int:
    repo = report.repository
    stats = report.commit_statistics
    total_commits: int = stats.total_commits if stats is not None else 0
    if repo.source == "github":
        stars_value: int = repo.stars + repo.watchers
        if stars_value:
            return _tier_points(stars_value, _STARS_TIERS)
    return _tier_points(total_commits, _LOCAL_COMMIT_TIERS)


def compute_health_score(
    report: AnalysisReport,
    *,
    now: datetime | None = None,
) -> HealthScore:
    """Score repository health 0-100 from recency, activity, community, and hygiene."""
    reference_now: datetime = now or datetime.now(UTC)
    stats = report.commit_statistics
    repo = report.repository

    recency_days = _recency_days(report, reference_now)
    recency: int = 0
    if recency_days is not None:
        recency = next(
            (points for threshold, points in _RECENCY_TIERS if recency_days <= threshold),
            3,
        )

    activity_days: int = stats.active_days if stats is not None else 0
    activity: int = _tier_points(activity_days, _ACTIVITY_TIERS)

    contributor_count: int = len({person.name for person in report.contributors})
    community: int = _tier_points(contributor_count, _COMMUNITY_TIERS)

    governance: int = 0
    notes: list[str] = []
    if repo.license is not None:
        governance += 8
    else:
        notes.append("No license detected")
    if repo.description:
        governance += 4
    else:
        notes.append("No description set")
    if repo.url:
        governance += 3
    else:
        notes.append("No remote URL configured")

    engagement: int = _engagement_points(report)

    if recency_days is not None and recency_days > 180:
        notes.append("Last activity was over 6 months ago")
    if contributor_count < 2:
        notes.append("Single-author history limits bus factor")

    breakdown = HealthBreakdown(
        recency=recency,
        activity=activity,
        community=community,
        governance=governance,
        engagement=engagement,
    )
    total = sum(breakdown.model_dump().values())
    grade = _grade_for(total)
    return HealthScore(total=total, grade=grade, breakdown=breakdown, notes=notes)


def _grade_for(total: int) -> str:
    if total >= 85:
        return "A"
    if total >= 70:
        return "B"
    if total >= 55:
        return "C"
    if total >= 40:
        return "D"
    return "F"


def enrich_report(report: AnalysisReport) -> AnalysisReport:
    """Attach computed language shares, commit statistics, and health score."""
    report.languages = compute_shares(report.languages)
    report.commit_statistics = compute_commit_statistics(report.commits)
    report.health_score = compute_health_score(report)
    return report


def build_monthly_activity(
    report: AnalysisReport,
    months: int = 12,
) -> list[int]:
    """Trailing per-month commit counts for sparkline rendering."""
    return monthly_activity(report.commits, months)
