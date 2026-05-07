"""Tests for report enrichment and sparkline rendering."""

from datetime import UTC, datetime

from analyzer.statistics import build_monthly_activity, enrich_report
from models.repository import (
    AnalysisReport,
    CommitInfo,
    LanguageUsage,
    RepositoryStats,
)
from utils.formatter import generate_sparkline


def _report() -> AnalysisReport:
    return AnalysisReport(
        repository=RepositoryStats(full_name="demo", source="local"),
        languages=[
            LanguageUsage(name="A", byte_size=100),
            LanguageUsage(name="B", byte_size=300),
        ],
        commits=[
            CommitInfo(
                sha="a",
                committed_at=datetime(2026, 7, 1, tzinfo=UTC),
                author_name="Ada",
                additions=5,
                deletions=1,
            ),
            CommitInfo(
                sha="b",
                committed_at=datetime(2026, 8, 1, tzinfo=UTC),
                author_name="Ada",
                additions=2,
                deletions=2,
            ),
        ],
    )


class TestEnrichReport:
    def test_attaches_statistics(self) -> None:
        report = enrich_report(_report())
        assert report.commit_statistics is not None
        assert report.commit_statistics.total_commits == 2
        assert report.commit_statistics.most_active_month in {"2026-07", "2026-08"}
        assert report.languages[0].name == "B"
        assert report.languages[0].share_pct == 75.0

    def test_monthly_activity_helper(self) -> None:
        report = enrich_report(_report())
        series = build_monthly_activity(report, months=3)
        assert series == [0, 1, 1]


class TestSparkline:
    def test_empty_data(self) -> None:
        assert generate_sparkline([]).plain == ""

    def test_flat_data_uses_mid_block(self) -> None:
        line: str = generate_sparkline([5, 5, 5]).plain
        assert line == "▅▅▅"

    def test_increasing_data_reaches_top_block(self) -> None:
        line: str = generate_sparkline([0, 1, 2, 3, 4]).plain
        assert line.endswith("█")
        assert line.startswith("▁")

    def test_length_preserved(self) -> None:
        assert len(generate_sparkline([3, 1, 4, 1, 5]).plain) == 5
