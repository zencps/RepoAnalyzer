"""Tests for report exporters (json/csv/md/html)."""

import csv
import io
import json
from datetime import UTC, datetime

import pytest

from analyzer.statistics import enrich_report
from models.repository import (
    AnalysisReport,
    CommitInfo,
    ContributorInfo,
    LanguageUsage,
    RepositoryStats,
)
from utils.exporters import (
    UnsupportedFormatError,
    export_report,
    infer_format,
    normalize_format,
    render_report_as,
)


@pytest.fixture(name="report")
def report_fixture() -> AnalysisReport:
    base = AnalysisReport(
        repository=RepositoryStats(
            full_name="octocat/demo",
            source="github",
            url="https://github.com/octocat/demo",
            description="demo repo",
            stars=100,
            forks=10,
            open_issues=2,
            watchers=5,
            license={"name": "MIT License", "spdx_id": "MIT"},
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2026, 8, 20, tzinfo=UTC),
        ),
        commits=[
            CommitInfo(
                sha="a" * 40,
                committed_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
                message="feat: add thing\n\nbody",
                author_name="Ada",
                additions=10,
                deletions=2,
            ),
            CommitInfo(
                sha="b" * 40,
                committed_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
                message="fix: bug",
                author_name="Grace",
                additions=3,
                deletions=3,
            ),
        ],
        contributors=[
            ContributorInfo(name="Ada", commit_count=7, share_pct=70.0),
            ContributorInfo(name="Grace", commit_count=3, share_pct=30.0),
        ],
        languages=[
            LanguageUsage(name="Python", byte_size=750),
            LanguageUsage(name="Rust", byte_size=250),
        ],
    )
    return enrich_report(base)


class TestNormalizeFormat:
    def test_aliases_and_case(self) -> None:
        assert normalize_format(".MD") == "md"
        assert normalize_format("markdown") == "md"
        assert normalize_format("htm") == "html"
        assert normalize_format("JSON") == "json"

    def test_unknown_raises_friendly(self) -> None:
        with pytest.raises(UnsupportedFormatError, match="Unsupported export format"):
            normalize_format("xlsx")

    def test_infer_from_suffix(self) -> None:
        assert infer_format(__import__("pathlib").Path("out/report.HTML")) == "html"


class TestJsonExporter:
    def test_valid_json_with_sections(self, report: AnalysisReport) -> None:
        payload = json.loads(render_report_as(report, "json"))
        assert payload["repository"]["full_name"] == "octocat/demo"
        assert payload["repository"]["license"]["spdx_id"] == "MIT"
        assert len(payload["commits"]) == 2
        assert payload["commit_statistics"]["total_commits"] == 2
        assert payload["languages"][0]["name"] in {"Python", "Rust"}

    def test_datetimes_iso_formatted(self, report: AnalysisReport) -> None:
        payload = json.loads(render_report_as(report, "json"))
        iso: str = payload["commits"][0]["committed_at"]
        assert "T" in iso


class TestCsvExporter:
    def test_sections_present(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "csv")
        for section in ("REPOSITORY", "COMMITS", "CONTRIBUTORS", "LANGUAGES"):
            assert section in content

    def test_rows_parse_and_align(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "csv")
        rows = list(csv.reader(io.StringIO(content)))
        header = ["sha", "committed_at", "author", "additions", "deletions", "message"]
        commit_header_index = rows.index(header)
        first_commit_row = rows[commit_header_index + 1]
        assert first_commit_row[0] == "a" * 40
        assert first_commit_row[2] == "Ada"
        assert first_commit_row[3] == "10"

    def test_multiline_message_flattened(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "csv")
        assert "feat: add thing body" in content


class TestMarkdownExporter:
    def test_structure(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "md")
        assert content.startswith("# RepoAnalyzer Report — octocat/demo")
        assert "## Snapshot" in content
        assert "## Commit Activity" in content
        assert "## Languages" in content
        assert "## Top Contributors" in content

    def test_language_bars_rendered(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "md")
        assert "█" in content and "░" in content
        assert "75.0%" in content

    def test_no_file_section_when_absent(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "md")
        assert "Biggest Files" not in content


class TestHtmlExporter:
    def test_full_document_with_content(self, report: AnalysisReport) -> None:
        content = render_report_as(report, "html")
        lowered = content.lower()
        assert "<html" in lowered
        assert "style=" in lowered
        assert "octocat/demo" in content
        assert "Ada" in content


class TestExportReportToFile:
    def test_writes_inferred_format(self, report: AnalysisReport, tmp_path) -> None:
        destination = tmp_path / "reports" / "out.json"
        written = export_report(report, destination)
        assert written == destination
        data = json.loads(destination.read_text(encoding="utf-8"))
        assert data["repository"]["source"] == "github"

    def test_format_override_beats_suffix(self, report: AnalysisReport, tmp_path) -> None:
        destination = tmp_path / "report.txt"
        export_report(report, destination, fmt="md")
        assert destination.read_text(encoding="utf-8").startswith("# RepoAnalyzer Report")
