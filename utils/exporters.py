"""Serializers that render AnalysisReport objects as JSON, CSV, Markdown, and HTML."""

import csv
import io
import json
import logging
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from models.repository import AnalysisReport
from utils.formatter import (
    REPO_ANALYZER_THEME,
    format_timestamp,
    humanize_bytes,
)
from utils.helpers import RepoAnalyzerError

logger: logging.Logger = logging.getLogger(__name__)

SUPPORTED_FORMATS: frozenset[str] = frozenset({"json", "csv", "md", "html"})
_FORMAT_ALIASES: dict[str, str] = {"markdown": "md", "htm": "html"}


class UnsupportedFormatError(RepoAnalyzerError):
    """Raised when an export format is not recognized."""


def normalize_format(fmt: str) -> str:
    cleaned: str = fmt.strip().lower().lstrip(".")
    cleaned = _FORMAT_ALIASES.get(cleaned, cleaned)
    if cleaned not in SUPPORTED_FORMATS:
        supported: str = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported export format '{fmt}'. Supported: {supported}."
        )
    return cleaned


def infer_format(destination: Path) -> str:
    return normalize_format(destination.suffix)


def export_report(
    report: AnalysisReport,
    destination: Path,
    fmt: str | None = None,
) -> Path:
    """Render the report and write it to `destination`, returning the path."""
    resolved_format: str = (
        normalize_format(fmt) if fmt is not None else infer_format(destination)
    )
    content: str = render_report_as(report, resolved_format)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    logger.debug("Wrote %s report to %s (%d bytes)", resolved_format, destination, len(content))
    return destination


def render_report_as(report: AnalysisReport, fmt: str) -> str:
    normalized: str = normalize_format(fmt)
    renderers: dict[str, Callable[[AnalysisReport], str]] = {
        "json": _to_json,
        "csv": _to_csv,
        "md": _to_markdown,
        "html": _to_html,
    }
    return renderers[normalized](report)


def _to_json(report: AnalysisReport) -> str:
    payload: dict[str, object] = report.model_dump(mode="json")
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _repository_rows(report: AnalysisReport) -> list[tuple[str, str]]:
    repo = report.repository
    stats = report.commit_statistics
    rows: list[tuple[str, str]] = [
        ("full_name", repo.full_name),
        ("source", repo.source),
        ("url", repo.url),
        ("default_branch", repo.default_branch),
        ("license", repo.license.name if repo.license else ""),
        ("stars", str(repo.stars)),
        ("forks", str(repo.forks)),
        ("open_issues", str(repo.open_issues)),
        ("watchers", str(repo.watchers)),
        ("size_kb", str(repo.size_kb)),
        ("total_commits", str(repo.total_commits or "")),
        ("total_contributors", str(repo.total_contributors or "")),
        ("created_at", format_timestamp(repo.created_at)),
        ("updated_at", format_timestamp(repo.updated_at)),
        ("pushed_at", format_timestamp(repo.pushed_at)),
    ]
    if stats is not None:
        rows.extend(
            [
                ("avg_commits_per_day", f"{stats.avg_per_day:g}"),
                ("active_days", str(stats.active_days)),
                ("most_active_month", stats.most_active_month or ""),
                ("avg_commit_size", _format_optional(stats.avg_commit_size)),
            ]
        )
    return rows


def _format_optional(value: float | int | None) -> str:
    return "" if value is None else f"{value:g}"


def _clean_message(message: str) -> str:
    return " ".join(message.split())


def _to_csv(report: AnalysisReport) -> str:
    buffer: io.StringIO = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    writer.writerow(["REPOSITORY"])
    writer.writerow(["field", "value"])
    for field, value in _repository_rows(report):
        writer.writerow([field, value])

    writer.writerow([])
    writer.writerow(["COMMITS"])
    writer.writerow(["sha", "committed_at", "author", "additions", "deletions", "message"])
    for commit in report.commits:
        writer.writerow(
            [
                commit.sha,
                commit.committed_at.isoformat(),
                commit.author_name,
                _format_optional(commit.additions),
                _format_optional(commit.deletions),
                _clean_message(commit.message),
            ]
        )

    writer.writerow([])
    writer.writerow(["CONTRIBUTORS"])
    writer.writerow(["rank", "name", "email", "commits", "share_pct"])
    for rank, person in enumerate(report.contributors, start=1):
        writer.writerow(
            [rank, person.name, person.email or "", person.commit_count, person.share_pct]
        )

    writer.writerow([])
    writer.writerow(["LANGUAGES"])
    writer.writerow(["language", "bytes", "share_pct"])
    for usage in report.languages:
        writer.writerow([usage.name, usage.byte_size, usage.share_pct])

    return buffer.getvalue()


def _bar(percentage: float, width: int = 20) -> str:
    clamped: float = max(0.0, min(percentage, 100.0))
    filled: int = round(clamped / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _to_markdown(report: AnalysisReport) -> str:
    repo = report.repository
    lines: list[str] = []
    append = lines.append

    append(f"# RepoAnalyzer Report — {repo.full_name}")
    append("")
    append(f"_Generated {report.generated_at.isoformat(timespec='seconds')} · Source: {repo.source}_")
    append("")
    if repo.description:
        append(f"> {repo.description}")
        append("")

    append("## Snapshot")
    append("")
    append("| Metric | Value |")
    append("| --- | ---: |")
    stats = report.commit_statistics
    commit_total: int = (
        stats.total_commits if stats is not None else repo.total_commits or 0
    )
    snapshot_rows: list[tuple[str, str]] = [
        ("Stars", f"{repo.stars:,}"),
        ("Forks", f"{repo.forks:,}"),
        ("Open issues", f"{repo.open_issues:,}"),
        ("Watchers", f"{repo.watchers:,}"),
        ("Commits", f"{commit_total:,}"),
        ("Contributors", str(repo.total_contributors or len(report.contributors))),
        ("License", repo.license.name if repo.license else "—"),
        ("Default branch", repo.default_branch),
        ("Created", format_timestamp(repo.created_at)),
        ("Last push", format_timestamp(repo.pushed_at)),
    ]
    if repo.local_path is not None:
        snapshot_rows.append(("Local path", f"`{repo.local_path.as_posix()}`"))
    for metric, value in snapshot_rows:
        append(f"| {metric} | {value} |")
    append("")

    stats = report.commit_statistics
    if stats is not None:
        append("## Commit Activity")
        append("")
        append(f"- Average per day: **{stats.avg_per_day:g}** over {stats.active_days} active days")
        peak: str = (
            f"**{stats.most_active_month}** ({stats.most_active_month_count} commits)"
            if stats.most_active_month
            else "—"
        )
        append(f"- Most active month: {peak}")
        size_note: str = (
            f"**~{stats.avg_commit_size:g} lines changed**"
            if stats.avg_commit_size is not None
            else "not computed"
        )
        append(f"- Average commit size: {size_note}")
        append(
            f"- History: {format_timestamp(stats.oldest_at)} → {format_timestamp(stats.latest_at)}"
        )
        append("")

    if report.languages:
        append("## Languages")
        append("")
        append("```text")
        for usage in report.languages:
            append(f"{usage.name:<14}{_bar(usage.share_pct)} {usage.share_pct:>5.1f}%")
        append("```")
        append("")

    if report.contributors:
        append("## Top Contributors")
        append("")
        append("| # | Author | Commits | Share |")
        append("| --: | --- | ---: | ---: |")
        for rank, person in enumerate(report.contributors, start=1):
            append(f"| {rank} | {person.name} | {person.commit_count} | {person.share_pct:.1f}% |")
        append("")

    files = report.file_analysis
    if files is not None and files.biggest_files:
        append("## Biggest Files")
        append("")
        append("| File | Size | LOC |")
        append("| --- | ---: | ---: |")
        for info in files.biggest_files[:10]:
            loc: str = str(info.lines_of_code) if info.lines_of_code is not None else "—"
            append(f"| `{info.path}` | {humanize_bytes(info.size_bytes)} | {loc} |")
        append("")
        append(
            f"_Scanned {files.total_files} files · "
            f"{files.total_lines_of_code:,} lines of code._"
        )
        append("")

    append("---")
    append("_Generated by RepoAnalyzer_")
    return "\n".join(lines) + "\n"


def _to_html(report: AnalysisReport) -> str:
    captured: Console = Console(
        record=True,
        width=100,
        theme=REPO_ANALYZER_THEME,
        legacy_windows=False,
    )
    from utils.tables import render_report

    render_report(report, out=captured)
    document: str = captured.export_html(inline_styles=True)
    title: str = f"RepoAnalyzer — {report.repository.full_name}"
    return document.replace("<title>Rich</title>", f"<title>{title}</title>")
