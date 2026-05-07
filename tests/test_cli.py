"""End-to-end CLI tests via Typer's CliRunner (offline only)."""

from pathlib import Path

from git import Repo
from typer.testing import CliRunner

from main import app

runner: CliRunner = CliRunner()


def compact(text: str) -> str:
    """Whitespace-insensitive matching, robust to Rich word-folding."""
    return "".join(text.split())


class TestGlobalOptions:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_help_lists_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "clone" in result.output
        assert "stats" in result.output

    def test_logo_printed_for_commands(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert "GitHub & Git Analytics" in result.output


class TestStatsCommand:
    def test_local_repository_analysis(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        result = runner.invoke(app, ["stats", str(path)])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert compact("sample (local)") in output
        assert compact("Repository Snapshot") in output
        assert compact("Commits 3") in output
        assert "AdaLovelace" in output

    def test_non_git_directory_fails_gracefully(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        result = runner.invoke(app, ["stats", str(plain)])
        assert result.exit_code == 1
        assert compact("Not a Git repository") in compact(result.output)
        assert "Traceback" not in result.output

    def test_missing_path_fails_gracefully(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["stats", str(tmp_path / "ghost")])
        assert result.exit_code == 1
        output: str = compact(result.output)
        assert compact("neither an existing directory") in output
        assert "Traceback" not in result.output

    def test_unrecognized_github_slug_fails_gracefully(self) -> None:
        result = runner.invoke(app, ["stats", "no-such-user-9f2x/no-such-repo-9f2x"])
        assert result.exit_code == 1
        output: str = compact(result.output)
        friendly_outcomes = (
            compact("Repository not found"),
            compact("rate limit exceeded"),
            compact("GitHub API error"),
        )
        assert any(phrase in output for phrase in friendly_outcomes)
        assert "Traceback" not in result.output


class TestCommitsCommand:
    def test_local_commit_analytics(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        result = runner.invoke(app, ["commits", str(path)])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert "CommitAnalytics" in output
        assert "Total3" in output
        assert "Mostactivemonth" in output
        assert "▄" in result.output or "█" in result.output

    def test_months_window_option(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        result = runner.invoke(app, ["commits", str(path), "--months", "6"])
        assert result.exit_code == 0


class TestContributorsCommand:
    def test_local_ranking(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        result = runner.invoke(app, ["contributors", str(path)])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert "TopContributors" in output
        assert "AdaLovelace" in output
        assert "GraceHopper" in output

    def test_top_option_limits_rows(self, local_repo: Repo) -> None:
        path: Path = Path(local_repo.working_dir)
        result = runner.invoke(app, ["contributors", str(path), "--top", "1"])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert "AdaLovelace" in output
        assert "GraceHopper" not in output


class TestLanguagesCommand:
    def test_local_directory_breakdown(self, poly_repo) -> None:
        result = runner.invoke(app, ["languages", str(poly_repo)])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert "Languages" in output
        assert "Python" in output
        assert "JavaScript" in output
        assert "node_modules" not in output

    def test_rejects_unknown_source(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["languages", str(tmp_path / "ghost")])
        assert result.exit_code == 1
        assert compact("neither an existing directory") in compact(result.output)


class TestAboutCommand:
    def test_shows_environment_summary(self) -> None:
        result = runner.invoke(app, ["about"])
        assert result.exit_code == 0
        output: str = compact(result.output)
        assert compact("GitHub token") in output
        assert "<notset>" in output
        assert "Clone" in output or "clonedirectory" in output.lower()

    def test_offline_by_default_no_api_call(self) -> None:
        result = runner.invoke(app, ["about"])
        assert result.exit_code == 0
        assert "requests remaining" not in compact(result.output)


class TestExportCommand:
    def test_json_export_from_local_repo(self, local_repo: Repo, tmp_path: Path) -> None:
        import json

        destination = tmp_path / "report.json"
        result = runner.invoke(app, ["export", str(destination), str(Path(local_repo.working_dir))])
        assert result.exit_code == 0
        assert destination.is_file()
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert payload["repository"]["source"] == "local"
        assert len(payload["commits"]) == 3
        assert compact("Report written to") in compact(result.output)

    def test_markdown_export_contains_sections(self, local_repo: Repo, tmp_path: Path) -> None:
        destination = tmp_path / "report.md"
        result = runner.invoke(app, ["export", str(destination), str(Path(local_repo.working_dir))])
        assert result.exit_code == 0
        content = destination.read_text(encoding="utf-8")
        assert content.startswith("# RepoAnalyzer Report")
        assert "## Snapshot" in content

    def test_html_export_creates_document(self, local_repo: Repo, tmp_path: Path) -> None:
        destination = tmp_path / "report.html"
        result = runner.invoke(app, ["export", str(destination), str(Path(local_repo.working_dir))])
        assert result.exit_code == 0
        lowered = destination.read_text(encoding="utf-8").lower()
        assert "<html" in lowered

    def test_unsupported_extension_fails_gracefully(self, local_repo: Repo, tmp_path: Path) -> None:
        destination = tmp_path / "report.xlsx"
        result = runner.invoke(app, ["export", str(destination), str(Path(local_repo.working_dir))])
        assert result.exit_code == 1
        assert compact("Unsupported export format") in compact(result.output)

    def test_format_override(self, local_repo: Repo, tmp_path: Path) -> None:
        import json as json_module

        destination = tmp_path / "snapshot.txt"
        result = runner.invoke(
            app,
            [
                "export",
                str(destination),
                str(Path(local_repo.working_dir)),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json_module.loads(destination.read_text(encoding="utf-8"))
        assert payload["repository"]["default_branch"] in {"master", "main"}


class TestCloneCommand:
    def test_unreachable_host_fails_gracefully(self) -> None:
        result = runner.invoke(
            app,
            ["clone", "https://no-such-host-9f2x.invalid/repo.git"],
        )
        assert result.exit_code == 1
        assert "Clone failed" in result.output or "not empty" in result.output
        assert "Traceback" not in result.output

    def test_existing_destination_aborts(self, tmp_path: Path) -> None:
        occupied = tmp_path / "occupied"
        occupied.mkdir()
        (occupied / "keep.txt").write_text("x", encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "clone",
                "https://github.com/octocat/Spoon-Knife.git",
                "--dest",
                str(occupied),
            ],
        )
        assert result.exit_code == 1
        assert "not empty" in result.output
