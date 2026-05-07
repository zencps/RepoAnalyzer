"""Tests for the composite health score and about/config surfaces."""

from datetime import UTC, datetime, timedelta

from analyzer.statistics import compute_commit_statistics, compute_health_score
from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    RepositoryStats,
)


def _report(
    *,
    pushed_at: datetime | None,
    contributors: int = 3,
    license_name: str | None = "MIT",
    description: str | None = "demo",
    url: str = "https://github.com/a/b",
    source: str = "github",
    active_days: int = 1,
) -> AnalysisReport:
    now = pushed_at or datetime(2020, 1, 1, tzinfo=UTC)
    total_commits = max(contributors, active_days)
    commits = [
        CommitInfo(
            sha=f"{i:040x}",
            committed_at=now - timedelta(days=i % active_days),
            author_name=f"dev{i % contributors}",
            additions=i,
            deletions=i,
        )
        for i in range(total_commits)
    ]
    people = [
        ContributorInfo(name=f"dev{i}", commit_count=i + 1) for i in range(contributors)
    ]
    report = AnalysisReport(
        repository=RepositoryStats(
            full_name="a/b",
            source=source,  # type: ignore[arg-type]
            description=description,
            url=url,
            pushed_at=pushed_at,
            license={"name": license_name} if license_name else None,
        ),
        commits=commits,
        contributors=people,
    )
    report.commit_statistics = compute_commit_statistics(commits)
    return report


class TestComputeHealthScore:
    def test_healthy_recent_repo_scores_high(self) -> None:
        now = datetime.now(UTC)
        report = _report(
            pushed_at=now - timedelta(days=2),
            contributors=12,
            active_days=35,
        )
        score = compute_health_score(report, now=now)
        assert score.total >= 85
        assert score.grade in {"A", "B"}
        assert score.notes == []

    def test_stale_unlicensed_repo_scores_low(self) -> None:
        now = datetime.now(UTC)
        report = _report(
            pushed_at=now - timedelta(days=400),
            contributors=1,
            license_name=None,
            description=None,
            url="",
        )
        score = compute_health_score(report, now=now)
        assert score.total <= 40
        assert score.grade == "F"
        assert "No license detected" in score.notes
        assert "Single-author history limits bus factor" in score.notes

    def test_recency_tiers_are_monotonic(self) -> None:
        now = datetime.now(UTC)
        recent = compute_health_score(_report(pushed_at=now - timedelta(days=5)), now=now)
        mid = compute_health_score(_report(pushed_at=now - timedelta(days=60)), now=now)
        old = compute_health_score(_report(pushed_at=now - timedelta(days=300)), now=now)
        assert recent.total >= mid.total >= old.total

    def test_unknown_dates_yield_zero_recency(self) -> None:
        empty = AnalysisReport(
            repository=RepositoryStats(full_name="x", source="github")
        )
        score = compute_health_score(empty, now=datetime.now(UTC))
        assert score.breakdown.recency == 0
        assert score.breakdown.activity == 0

    def test_local_engagement_uses_commit_count(self) -> None:
        from analyzer.statistics import enrich_report

        report = _report(pushed_at=datetime.now(UTC), source="local")
        big = AnalysisReport.model_validate(report.model_dump(mode="json"))
        big.commits.extend(
            CommitInfo(
                sha=f"c{i:040x}",
                committed_at=datetime.now(UTC),
                author_name="dev0",
            )
            for i in range(600)
        )

        enrich_report(big)
        assert big.health_score is not None
        assert big.health_score.breakdown.engagement == 10


class TestHealthPanelIntegration:
    def test_render_report_shows_health_panel(self) -> None:
        from io import StringIO

        from rich.console import Console

        from analyzer.statistics import enrich_report
        from utils.formatter import REPO_ANALYZER_THEME
        from utils.tables import render_report

        report = enrich_report(_report(pushed_at=datetime.now(UTC)))
        buffer = StringIO()
        console = Console(file=buffer, width=120, theme=REPO_ANALYZER_THEME)
        render_report(report, out=console)
        output = buffer.getvalue()
        assert "Repository Health" in output
        assert "/100" in output
