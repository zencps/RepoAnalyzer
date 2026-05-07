"""Tests for Rich table/panel builders."""

from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    LanguageUsage,
    RepositoryStats,
)
from utils.formatter import REPO_ANALYZER_THEME
from utils.tables import (
    build_contributors_table,
    build_languages_table,
    build_stats_table,
    build_summary_panel,
    render_report,
)


def make_renderer() -> object:
    def render(renderable: object) -> str:
        buffer = StringIO()
        console = Console(
            file=buffer,
            width=120,
            theme=REPO_ANALYZER_THEME,
            legacy_windows=False,
            highlight=False,
        )
        console.print(renderable)
        return buffer.getvalue()

    return render


@pytest.fixture(name="render")
def render_fixture() -> object:
    return make_renderer()


@pytest.fixture(name="github_stats")
def github_stats_fixture() -> RepositoryStats:
    return RepositoryStats(
        full_name="octocat/Spoon-Knife",
        source="github",
        url="https://github.com/octocat/Spoon-Knife",
        description="This repository is for demonstration purposes.",
        default_branch="main",
        stars=12_345,
        forks=4_321,
        open_issues=17,
        watchers=110,
        size_kb=2048,
        total_commits=350,
        total_contributors=42,
        license={"name": "MIT License", "spdx_id": "MIT"},
        created_at=datetime(2013, 1, 1, tzinfo=UTC),
        pushed_at=datetime(2026, 8, 1, 9, 30, tzinfo=UTC),
    )


class TestBuildStatsTable:
    def test_contains_core_metrics(
        self, render: object, github_stats: RepositoryStats
    ) -> None:
        output: str = render(build_stats_table(github_stats))
        for needle in ("Stars", "12,345", "Forks", "MIT License", "GitHub"):
            assert needle in output

    def test_unknown_values_render_em_dash(self, render: object) -> None:
        local = RepositoryStats(full_name="demo (local)", source="local")
        output: str = render(build_stats_table(local))
        assert output.count("—") >= 5


class TestSummaryPanel:
    def test_snapshot_contains_metrics_and_path(
        self, render: object, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        stats = RepositoryStats(
            full_name="demo (local)",
            source="local",
            total_commits=7,
            local_path=tmp_path_factory.mktemp("x"),
        )
        output: str = render(build_summary_panel(stats))
        assert "Repository Snapshot" in output
        assert "Commits 7" in output


class TestContributorsTable:
    def test_ranking_rows(self, render: object) -> None:
        contributors = [
            ContributorInfo(name="Ada", commit_count=30, email="a@x.io"),
            ContributorInfo(name="Grace", commit_count=12),
        ]
        output: str = render(build_contributors_table(contributors))
        for needle in ("Top Contributors", "Ada", "Grace", "30", "12"):
            assert needle in output


class TestLanguagesTable:
    def test_bars_and_sizes(self, render: object) -> None:
        languages = [LanguageUsage(name="Python", byte_size=2500, share_pct=73.0)]
        output: str = render(build_languages_table(languages))
        assert "Python" in output
        assert "2.4 KB" in output
        assert "█" in output
        assert "73.0%" in output

    def test_zero_share_bar_is_empty(self, render: object) -> None:
        languages = [LanguageUsage(name="Shell", byte_size=10)]
        output: str = render(build_languages_table(languages))
        assert "░░░░░░░░░░" in output


class TestRenderReport:
    def test_renders_all_populated_sections(self, render: object, github_stats: RepositoryStats) -> None:
        buffer = StringIO()
        themed_console = Console(
            file=buffer,
            width=120,
            theme=REPO_ANALYZER_THEME,
            legacy_windows=False,
            highlight=False,
        )
        report = AnalysisReport(
            repository=github_stats,
            contributors=[ContributorInfo(name="Ada", commit_count=5)],
            languages=[LanguageUsage(name="Ruby", byte_size=100)],
            commits=[
                CommitInfo(sha="a" * 40, committed_at=datetime.now(UTC), message="m")
            ],
        )
        render_report(report, out=themed_console)
        output: str = buffer.getvalue()
        for needle in ("Repository Snapshot", "Stars", "Top Contributors", "Languages"):
            assert needle in output

    def test_skips_empty_sections(self, render: object, github_stats: RepositoryStats) -> None:
        buffer = StringIO()
        themed_console = Console(
            file=buffer,
            width=120,
            theme=REPO_ANALYZER_THEME,
            legacy_windows=False,
            highlight=False,
        )
        report = AnalysisReport(repository=github_stats)
        render_report(report, out=themed_console)
        output: str = buffer.getvalue()
        assert "Top Contributors" not in output
        assert "Languages" not in output
